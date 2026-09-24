import pytest

from app.services.goal_dataset import (
    GoalAnnotation,
    GoalDatasetError,
    HardNegativePrediction,
    build_hard_negative_samples,
    build_goal_dataset_samples,
)


def test_reviewed_false_positives_become_hard_negative_samples():
    samples = build_hard_negative_samples(
        match_id=1,
        video_id=2,
        video_storage_key="match.mp4",
        duration_seconds=100,
        predictions=[
            HardNegativePrediction(prediction_id=7, timestamp_seconds=30),
            HardNegativePrediction(prediction_id=8, timestamp_seconds=31),
            HardNegativePrediction(prediction_id=9, timestamp_seconds=70),
        ],
    )

    assert [sample.sample_id for sample in samples] == [
        "m1-v2-hard-negative-0007",
        "m1-v2-hard-negative-0009",
    ]
    assert all(sample.label == "non_goal" for sample in samples)


def test_builds_balanced_time_split_goal_dataset() -> None:
    samples = build_goal_dataset_samples(
        match_id=1,
        video_id=2,
        video_storage_key="1/match.mp4",
        duration_seconds=500,
        expected_goal_count=4,
        annotations=[
            GoalAnnotation(event_id=10, timestamp_seconds=60),
            GoalAnnotation(event_id=11, timestamp_seconds=180),
            GoalAnnotation(event_id=12, timestamp_seconds=320),
            GoalAnnotation(event_id=13, timestamp_seconds=450),
        ],
    )

    assert len(samples) == 8
    assert sum(sample.label == "goal" for sample in samples) == 4
    assert sum(sample.label == "non_goal" for sample in samples) == 4
    assert sum(sample.split == "train" and sample.label == "goal" for sample in samples) == 3
    assert sum(sample.split == "train" and sample.label == "non_goal" for sample in samples) == 3
    assert sum(sample.split == "validation" and sample.label == "goal" for sample in samples) == 1
    assert sum(sample.split == "validation" and sample.label == "non_goal" for sample in samples) == 1
    assert all(
        20
        <= min(
            abs(negative.center_seconds - positive.center_seconds)
            for positive in samples
            if positive.label == "goal"
        )
        <= 90
        for negative in samples
        if negative.label == "non_goal"
    )


def test_rejects_incomplete_goal_annotations() -> None:
    with pytest.raises(GoalDatasetError, match="最终比分总进球数"):
        build_goal_dataset_samples(
            match_id=1,
            video_id=2,
            video_storage_key="1/match.mp4",
            duration_seconds=500,
            expected_goal_count=3,
            annotations=[GoalAnnotation(event_id=10, timestamp_seconds=60)],
        )


def test_rejects_duplicate_goal_timestamps() -> None:
    with pytest.raises(GoalDatasetError, match="重复进球标注"):
        build_goal_dataset_samples(
            match_id=1,
            video_id=2,
            video_storage_key="1/match.mp4",
            duration_seconds=500,
            expected_goal_count=2,
            annotations=[
                GoalAnnotation(event_id=10, timestamp_seconds=60),
                GoalAnnotation(event_id=11, timestamp_seconds=61),
            ],
        )
