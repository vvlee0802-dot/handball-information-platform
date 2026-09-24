from app.services.goal_detection import (
    MODEL_FRAME_SIZE,
    GoalCandidatePrediction,
    collapse_positive_windows,
    model_scan_filter,
)


def test_collapse_positive_windows_keeps_strongest_from_each_run():
    collapsed = collapse_positive_windows(
        [
            GoalCandidatePrediction(timestamp_seconds=10, confidence=0.72),
            GoalCandidatePrediction(timestamp_seconds=15, confidence=0.91),
            GoalCandidatePrediction(timestamp_seconds=20, confidence=0.84),
            GoalCandidatePrediction(timestamp_seconds=35, confidence=0.76),
            GoalCandidatePrediction(timestamp_seconds=40, confidence=0.88),
        ]
    )

    assert collapsed == [
        GoalCandidatePrediction(timestamp_seconds=15, confidence=0.91),
        GoalCandidatePrediction(timestamp_seconds=40, confidence=0.88),
    ]


def test_model_scan_uses_same_square_crop_size_as_training_preprocessing():
    assert MODEL_FRAME_SIZE == 256
    assert model_scan_filter() == "fps=2,scale=-2:256,crop=256:256"
