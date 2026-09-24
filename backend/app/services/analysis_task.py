from datetime import UTC, datetime
from pathlib import Path
import subprocess
from typing import Callable

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis_task import AnalysisTask
from app.models.match import Match
from app.models.video import Video
from app.repositories import analysis_prediction as analysis_predictions
from app.repositories import event as events
from app.services.clip_export import get_ffmpeg_executable
from app.services.goal_detection import (
    GoalCandidatePrediction,
    GoalDetectionResult,
    detect_goal_candidates,
)
from app.services.goal_evaluation import evaluate_goal_predictions


class AnalysisTaskError(Exception):
    pass


def scan_video_frames(
    path: Path,
    duration_seconds: float | None,
    on_progress: Callable[[int], None],
) -> None:
    command = [
        get_ffmpeg_executable(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-progress",
        "pipe:1",
        "-nostats",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-vf",
        "fps=1/5",
        "-an",
        "-f",
        "null",
        "-",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    last_progress = 10
    if process.stdout is None:
        process.kill()
        raise AnalysisTaskError("无法读取视频分析进度。")

    for line in process.stdout:
        key, separator, raw_value = line.strip().partition("=")
        if separator == "" or key not in {"out_time_ms", "out_time_us"}:
            continue
        if duration_seconds is None or duration_seconds <= 0:
            continue
        try:
            analyzed_seconds = int(raw_value) / 1_000_000
        except ValueError:
            continue
        progress = min(95, 10 + int((analyzed_seconds / duration_seconds) * 85))
        if progress >= last_progress + 5:
            on_progress(progress)
            last_progress = progress

    stderr = process.stderr.read().strip() if process.stderr is not None else ""
    return_code = process.wait()
    if return_code != 0:
        detail = stderr.splitlines()[-1] if stderr else "未知视频解码错误"
        raise AnalysisTaskError(f"视频分析失败：{detail}"[:1000])


def process_analysis_task(task_id: str, bind: Engine) -> None:
    with Session(bind=bind) as db:
        task = db.get(AnalysisTask, task_id)
        if task is None or task.status != "queued":
            return

        task.status = "running"
        task.stage = "preparing"
        task.progress = 5
        task.failure_reason = None
        task.processing_started_at = datetime.now(UTC)
        task.processing_completed_at = None
        db.commit()

        try:
            video = db.get(Video, task.video_id)
            if video is None or video.deleted_at is not None:
                raise AnalysisTaskError("分析任务关联的视频不存在。")
            source_path = settings.video_storage_path / video.storage_key
            if not source_path.is_file():
                raise AnalysisTaskError("找不到视频文件，请确认存储目录后重试。")

            task.stage = "scanning_frames"
            task.progress = 10
            db.commit()

            def update_progress(progress: int) -> None:
                task.progress = progress
                db.commit()

            result = detect_goal_candidates(
                source_path,
                video.duration_seconds,
                update_progress,
            )
            predictions = normalize_predictions(
                result,
                video.duration_seconds,
            )
            if predictions and result.model_version is None:
                raise AnalysisTaskError("模型返回候选事件时必须提供模型版本。")
            match = db.get(Match, task.match_id)
            if match is None:
                raise AnalysisTaskError("分析任务关联的比赛不存在。")
            ground_truth_events = events.list_verified_manual_goals(
                db,
                match_id=task.match_id,
                video_id=task.video_id,
            )
            expected_goal_count = (
                match.home_score + match.away_score
                if match.home_score is not None and match.away_score is not None
                else None
            )
            has_complete_ground_truth = (
                result.model_version is not None
                and expected_goal_count is not None
                and expected_goal_count > 0
                and len(ground_truth_events) == expected_goal_count
            )
            if has_complete_ground_truth:
                evaluation = evaluate_goal_predictions(
                    [event.timestamp_seconds for event in ground_truth_events],
                    predictions,
                )
                analysis_predictions.replace_evaluation_predictions(
                    db,
                    task_id=task.id,
                    ground_truth_events=ground_truth_events,
                    predictions=predictions,
                    evaluation=evaluation,
                )
                task.evaluation_mode = True
                task.ground_truth_count = evaluation.ground_truth_count
                task.true_positive_count = evaluation.true_positive_count
                task.false_positive_count = evaluation.false_positive_count
                task.false_negative_count = evaluation.false_negative_count
                task.precision = evaluation.precision
                task.recall = evaluation.recall
                task.f1 = evaluation.f1
                task.mean_absolute_error_seconds = evaluation.mean_absolute_error_seconds
            elif predictions:
                events.soft_delete_ai_drafts_for_video(
                    db,
                    video_id=task.video_id,
                    user_id=task.created_by_user_id,
                )
                events.create_ai_candidates(
                    db,
                    match_id=task.match_id,
                    video_id=task.video_id,
                    analysis_task_id=task.id,
                    model_version=result.model_version or "",
                    predictions=predictions,
                    user_id=task.created_by_user_id,
                )
            task.model_version = result.model_version
            task.candidate_count = len(predictions)
            task.status = "completed"
            task.stage = (
                "completed_evaluation"
                if has_complete_ground_truth
                else "completed"
                if result.model_version is not None
                else "completed_no_model"
            )
            task.progress = 100
            task.processing_completed_at = datetime.now(UTC)
            db.commit()
        except (AnalysisTaskError, OSError, RuntimeError) as error:
            task.status = "failed"
            task.stage = "failed"
            task.failure_reason = str(error)[:1000]
            task.processing_completed_at = datetime.now(UTC)
            db.commit()


def normalize_predictions(
    result: GoalDetectionResult,
    duration_seconds: float | None,
) -> list[GoalCandidatePrediction]:
    valid: list[GoalCandidatePrediction] = []
    for prediction in sorted(
        result.candidates,
        key=lambda candidate: (candidate.timestamp_seconds, -candidate.confidence),
    ):
        if prediction.timestamp_seconds < 0:
            continue
        if duration_seconds is not None and prediction.timestamp_seconds > duration_seconds:
            continue
        if not 0 <= prediction.confidence <= 1:
            continue
        if valid and prediction.timestamp_seconds - valid[-1].timestamp_seconds < 3:
            if prediction.confidence > valid[-1].confidence:
                valid[-1] = prediction
            continue
        valid.append(prediction)
    return valid
