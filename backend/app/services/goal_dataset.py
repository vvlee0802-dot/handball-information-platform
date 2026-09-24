from dataclasses import asdict, dataclass
import math


EVENT_LEAD_SECONDS = 8.0
EVENT_TRAIL_SECONDS = 5.0
NEGATIVE_MIN_DISTANCE_SECONDS = 20.0
NEGATIVE_MAX_DISTANCE_SECONDS = 90.0
NEGATIVE_CANDIDATE_STEP_SECONDS = 5.0
VALIDATION_FRACTION = 0.2


class GoalDatasetError(Exception):
    pass


@dataclass(frozen=True)
class GoalAnnotation:
    event_id: int
    timestamp_seconds: float


@dataclass(frozen=True)
class GoalDatasetSample:
    sample_id: str
    match_id: int
    video_id: int
    video_storage_key: str
    split: str
    label: str
    label_id: int
    center_seconds: float
    start_seconds: float
    end_seconds: float
    event_id: int | None

    def to_dict(self) -> dict[str, str | int | float | None]:
        return asdict(self)


@dataclass(frozen=True)
class HardNegativePrediction:
    prediction_id: int
    timestamp_seconds: float


def _split_for_timestamp(timestamp_seconds: float, duration_seconds: float) -> str:
    validation_start = duration_seconds * (1 - VALIDATION_FRACTION)
    return "validation" if timestamp_seconds >= validation_start else "train"


def _clip_bounds(center_seconds: float, duration_seconds: float) -> tuple[float, float]:
    return (
        max(0.0, center_seconds - EVENT_LEAD_SECONDS),
        min(duration_seconds, center_seconds + EVENT_TRAIL_SECONDS),
    )


def _select_evenly(candidates: list[float], count: int) -> list[float]:
    if count == 0:
        return []
    if len(candidates) < count:
        raise GoalDatasetError(
            f"负样本候选不足：需要 {count} 个，实际只有 {len(candidates)} 个。"
        )
    return [candidates[math.floor((index + 0.5) * len(candidates) / count)] for index in range(count)]


def build_goal_dataset_samples(
    *,
    match_id: int,
    video_id: int,
    video_storage_key: str,
    duration_seconds: float,
    expected_goal_count: int,
    annotations: list[GoalAnnotation],
) -> list[GoalDatasetSample]:
    if duration_seconds <= EVENT_LEAD_SECONDS + EVENT_TRAIL_SECONDS:
        raise GoalDatasetError("视频时长不足，无法生成训练片段。")
    ordered_annotations = sorted(annotations, key=lambda item: item.timestamp_seconds)
    if len(ordered_annotations) != expected_goal_count:
        raise GoalDatasetError(
            f"已确认进球数 {len(ordered_annotations)} 与最终比分总进球数 "
            f"{expected_goal_count} 不一致。"
        )
    timestamps = [annotation.timestamp_seconds for annotation in ordered_annotations]
    if any(timestamp < 0 or timestamp > duration_seconds for timestamp in timestamps):
        raise GoalDatasetError("存在超出视频范围的进球时间。")
    if any(
        current - previous < 3
        for previous, current in zip(timestamps, timestamps[1:])
    ):
        raise GoalDatasetError("存在三秒内的重复进球标注，请先检查事件时间。")

    positive_samples: list[GoalDatasetSample] = []
    for index, annotation in enumerate(ordered_annotations, start=1):
        start, end = _clip_bounds(annotation.timestamp_seconds, duration_seconds)
        positive_samples.append(
            GoalDatasetSample(
                sample_id=f"m{match_id}-v{video_id}-goal-{index:03d}",
                match_id=match_id,
                video_id=video_id,
                video_storage_key=video_storage_key,
                split=_split_for_timestamp(annotation.timestamp_seconds, duration_seconds),
                label="goal",
                label_id=1,
                center_seconds=annotation.timestamp_seconds,
                start_seconds=start,
                end_seconds=end,
                event_id=annotation.event_id,
            )
        )

    candidate_centers: dict[str, list[float]] = {"train": [], "validation": []}
    center = EVENT_LEAD_SECONDS
    while center <= duration_seconds - EVENT_TRAIL_SECONDS:
        nearest_goal_distance = min(abs(center - goal_time) for goal_time in timestamps)
        if (
            NEGATIVE_MIN_DISTANCE_SECONDS
            <= nearest_goal_distance
            <= NEGATIVE_MAX_DISTANCE_SECONDS
        ):
            candidate_centers[_split_for_timestamp(center, duration_seconds)].append(center)
        center += NEGATIVE_CANDIDATE_STEP_SECONDS

    negative_samples: list[GoalDatasetSample] = []
    negative_index = 1
    for split in ("train", "validation"):
        positive_count = sum(sample.split == split for sample in positive_samples)
        selected_centers = _select_evenly(candidate_centers[split], positive_count)
        for center in selected_centers:
            start, end = _clip_bounds(center, duration_seconds)
            negative_samples.append(
                GoalDatasetSample(
                    sample_id=f"m{match_id}-v{video_id}-non-goal-{negative_index:03d}",
                    match_id=match_id,
                    video_id=video_id,
                    video_storage_key=video_storage_key,
                    split=split,
                    label="non_goal",
                    label_id=0,
                    center_seconds=center,
                    start_seconds=start,
                    end_seconds=end,
                    event_id=None,
                )
            )
            negative_index += 1

    return sorted(
        [*positive_samples, *negative_samples],
        key=lambda sample: (sample.split, sample.center_seconds, -sample.label_id),
    )


def build_hard_negative_samples(
    *,
    match_id: int,
    video_id: int,
    video_storage_key: str,
    duration_seconds: float,
    predictions: list[HardNegativePrediction],
) -> list[GoalDatasetSample]:
    samples: list[GoalDatasetSample] = []
    previous_timestamp: float | None = None
    for prediction in sorted(predictions, key=lambda item: item.timestamp_seconds):
        if previous_timestamp is not None and prediction.timestamp_seconds - previous_timestamp < 3:
            continue
        if not 0 <= prediction.timestamp_seconds <= duration_seconds:
            continue
        start, end = _clip_bounds(prediction.timestamp_seconds, duration_seconds)
        samples.append(
            GoalDatasetSample(
                sample_id=f"m{match_id}-v{video_id}-hard-negative-{prediction.prediction_id:04d}",
                match_id=match_id,
                video_id=video_id,
                video_storage_key=video_storage_key,
                split=_split_for_timestamp(prediction.timestamp_seconds, duration_seconds),
                label="non_goal",
                label_id=0,
                center_seconds=prediction.timestamp_seconds,
                start_seconds=start,
                end_seconds=end,
                event_id=None,
            )
        )
        previous_timestamp = prediction.timestamp_seconds
    return samples
