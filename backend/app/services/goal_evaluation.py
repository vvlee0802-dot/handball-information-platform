from dataclasses import dataclass

from app.services.goal_detection import GoalCandidatePrediction


MATCH_TOLERANCE_SECONDS = 8.0


@dataclass(frozen=True)
class GoalEvaluationMatch:
    ground_truth_index: int
    prediction_index: int
    time_error_seconds: float


@dataclass(frozen=True)
class GoalEvaluation:
    ground_truth_count: int
    prediction_count: int
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    precision: float
    recall: float
    f1: float
    mean_absolute_error_seconds: float | None
    matches: tuple[GoalEvaluationMatch, ...]
    false_positive_prediction_indices: tuple[int, ...]
    false_negative_ground_truth_indices: tuple[int, ...]


def evaluate_goal_predictions(
    ground_truth_timestamps: list[float],
    predictions: list[GoalCandidatePrediction],
    *,
    tolerance_seconds: float = MATCH_TOLERANCE_SECONDS,
) -> GoalEvaluation:
    if tolerance_seconds <= 0:
        raise ValueError("Matching tolerance must be greater than zero")

    possible_matches = sorted(
        (
            (abs(prediction.timestamp_seconds - truth), truth_index, prediction_index)
            for truth_index, truth in enumerate(ground_truth_timestamps)
            for prediction_index, prediction in enumerate(predictions)
            if abs(prediction.timestamp_seconds - truth) <= tolerance_seconds
        ),
        key=lambda item: (item[0], item[1], item[2]),
    )
    matched_truth: set[int] = set()
    matched_predictions: set[int] = set()
    errors: list[float] = []
    matches: list[GoalEvaluationMatch] = []
    for error, truth_index, prediction_index in possible_matches:
        if truth_index in matched_truth or prediction_index in matched_predictions:
            continue
        matched_truth.add(truth_index)
        matched_predictions.add(prediction_index)
        errors.append(error)
        matches.append(
            GoalEvaluationMatch(
                ground_truth_index=truth_index,
                prediction_index=prediction_index,
                time_error_seconds=error,
            )
        )

    true_positive = len(errors)
    false_positive = len(predictions) - true_positive
    false_negative = len(ground_truth_timestamps) - true_positive
    precision = true_positive / len(predictions) if predictions else 0.0
    recall = true_positive / len(ground_truth_timestamps) if ground_truth_timestamps else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return GoalEvaluation(
        ground_truth_count=len(ground_truth_timestamps),
        prediction_count=len(predictions),
        true_positive_count=true_positive,
        false_positive_count=false_positive,
        false_negative_count=false_negative,
        precision=precision,
        recall=recall,
        f1=f1,
        mean_absolute_error_seconds=sum(errors) / len(errors) if errors else None,
        matches=tuple(matches),
        false_positive_prediction_indices=tuple(
            index for index in range(len(predictions)) if index not in matched_predictions
        ),
        false_negative_ground_truth_indices=tuple(
            index
            for index in range(len(ground_truth_timestamps))
            if index not in matched_truth
        ),
    )
