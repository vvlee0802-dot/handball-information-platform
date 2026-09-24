import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.event import Event
from app.models.analysis_prediction import AnalysisPrediction
from app.models.analysis_task import AnalysisTask
from app.models.match import Match
from app.models.video import Video
from app.services.goal_dataset import (
    EVENT_LEAD_SECONDS,
    EVENT_TRAIL_SECONDS,
    GoalAnnotation,
    GoalDatasetError,
    HardNegativePrediction,
    NEGATIVE_MAX_DISTANCE_SECONDS,
    NEGATIVE_MIN_DISTANCE_SECONDS,
    VALIDATION_FRACTION,
    build_goal_dataset_samples,
    build_hard_negative_samples,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a reproducible goal-detection dataset manifest"
    )
    parser.add_argument("--match-id", type=int, required=True)
    parser.add_argument("--video-id", type=int)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("datasets/goal_detection"),
    )
    return parser.parse_args()


def select_video(videos: list[Video], requested_video_id: int | None) -> Video:
    if requested_video_id is not None:
        selected = next((video for video in videos if video.id == requested_video_id), None)
        if selected is None:
            raise GoalDatasetError("指定的视频不属于该比赛或当前不可用。")
        return selected
    original_videos = [video for video in videos if video.video_type == "original"]
    if len(original_videos) != 1:
        raise GoalDatasetError("比赛必须恰好有一段可用的原始录像，或通过 --video-id 指定。")
    return original_videos[0]


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        match = db.get(Match, args.match_id)
        if match is None:
            raise SystemExit("Match not found.")
        if match.home_score is None or match.away_score is None:
            raise SystemExit("比赛缺少最终比分，无法验证进球标注是否完整。")
        videos = list(
            db.scalars(
                select(Video).where(
                    Video.match_id == match.id,
                    Video.deleted_at.is_(None),
                    Video.processing_status == "completed",
                )
            )
        )
        try:
            video = select_video(videos, args.video_id)
        except GoalDatasetError as error:
            raise SystemExit(str(error)) from error
        if video.duration_seconds is None:
            raise SystemExit("视频缺少时长，无法生成数据集。")
        source_path = settings.video_storage_path / video.storage_key
        if not source_path.is_file():
            raise SystemExit("视频文件不存在，无法生成数据集。")

        events = list(
            db.scalars(
                select(Event)
                .where(
                    Event.match_id == match.id,
                    Event.video_id == video.id,
                    Event.event_type == "goal",
                    Event.source == "manual",
                    Event.status == "verified",
                    Event.deleted_at.is_(None),
                )
                .order_by(Event.timestamp_seconds, Event.id)
            )
        )
        try:
            samples = build_goal_dataset_samples(
                match_id=match.id,
                video_id=video.id,
                video_storage_key=video.storage_key,
                duration_seconds=video.duration_seconds,
                expected_goal_count=match.home_score + match.away_score,
                annotations=[
                    GoalAnnotation(event_id=event.id, timestamp_seconds=event.timestamp_seconds)
                    for event in events
                ],
            )
        except GoalDatasetError as error:
            raise SystemExit(str(error)) from error
        reviewed_false_positives = list(
            db.execute(
                select(
                    AnalysisPrediction.id,
                    AnalysisPrediction.predicted_timestamp_seconds,
                )
                .join(
                    AnalysisTask,
                    AnalysisTask.id == AnalysisPrediction.analysis_task_id,
                )
                .where(
                    AnalysisTask.match_id == match.id,
                    AnalysisTask.video_id == video.id,
                    AnalysisPrediction.outcome == "false_positive",
                    AnalysisPrediction.training_decision == "include",
                    AnalysisPrediction.predicted_timestamp_seconds.is_not(None),
                )
            )
        )
        hard_negative_samples = build_hard_negative_samples(
            match_id=match.id,
            video_id=video.id,
            video_storage_key=video.storage_key,
            duration_seconds=video.duration_seconds,
            predictions=[
                HardNegativePrediction(
                    prediction_id=prediction_id,
                    timestamp_seconds=timestamp_seconds,
                )
                for prediction_id, timestamp_seconds in reviewed_false_positives
            ],
        )
        samples.extend(hard_negative_samples)
        samples.sort(key=lambda sample: (sample.split, sample.center_seconds, -sample.label_id))

    output_dir = args.output_dir.resolve() / f"match-{args.match_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n" for sample in samples),
        encoding="utf-8",
    )
    distribution = Counter((sample.split, sample.label) for sample in samples)
    metadata = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "match_id": args.match_id,
        "video_id": video.id,
        "video_storage_key": video.storage_key,
        "video_duration_seconds": video.duration_seconds,
        "expected_goal_count": match.home_score + match.away_score,
        "confirmed_goal_count": len(events),
        "sample_count": len(samples),
        "reviewed_hard_negative_count": len(hard_negative_samples),
        "sample_window_seconds": {
            "before": EVENT_LEAD_SECONDS,
            "after": EVENT_TRAIL_SECONDS,
        },
        "negative_goal_distance_seconds": {
            "minimum": NEGATIVE_MIN_DISTANCE_SECONDS,
            "maximum": NEGATIVE_MAX_DISTANCE_SECONDS,
        },
        "validation_fraction": VALIDATION_FRACTION,
        "distribution": {
            f"{split}_{label}": count
            for (split, label), count in sorted(distribution.items())
        },
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {manifest_path}")
    print(json.dumps(metadata["distribution"], ensure_ascii=False))


if __name__ == "__main__":
    main()
