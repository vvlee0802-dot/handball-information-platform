import pytest

from app.services.goal_detection import GoalCandidatePrediction
from app.services.goal_evaluation import evaluate_goal_predictions


def test_goal_evaluation_matches_each_prediction_and_truth_once():
    result = evaluate_goal_predictions(
        [10, 30, 40],
        [
            GoalCandidatePrediction(timestamp_seconds=11, confidence=0.9),
            GoalCandidatePrediction(timestamp_seconds=13, confidence=0.8),
            GoalCandidatePrediction(timestamp_seconds=37, confidence=0.7),
            GoalCandidatePrediction(timestamp_seconds=80, confidence=0.95),
        ],
    )

    assert result.true_positive_count == 2
    assert result.false_positive_count == 2
    assert result.false_negative_count == 1
    assert result.precision == 0.5
    assert result.recall == pytest.approx(2 / 3)
    assert result.f1 == pytest.approx(4 / 7)
    assert result.mean_absolute_error_seconds == 2


def test_goal_evaluation_handles_no_predictions():
    result = evaluate_goal_predictions([10, 20], [])

    assert result.true_positive_count == 0
    assert result.false_positive_count == 0
    assert result.false_negative_count == 2
    assert result.precision == 0
    assert result.recall == 0
    assert result.f1 == 0
    assert result.mean_absolute_error_seconds is None
