from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.analysis_prediction import AnalysisPrediction
from app.models.event import Event
from app.services.goal_detection import GoalCandidatePrediction
from app.services.goal_evaluation import GoalEvaluation


def replace_evaluation_predictions(
    db: Session,
    *,
    task_id: str,
    ground_truth_events: list[Event],
    predictions: list[GoalCandidatePrediction],
    evaluation: GoalEvaluation,
) -> list[AnalysisPrediction]:
    db.execute(
        delete(AnalysisPrediction).where(AnalysisPrediction.analysis_task_id == task_id)
    )
    items: list[AnalysisPrediction] = []
    for match in evaluation.matches:
        event = ground_truth_events[match.ground_truth_index]
        prediction = predictions[match.prediction_index]
        items.append(
            AnalysisPrediction(
                analysis_task_id=task_id,
                outcome="true_positive",
                predicted_timestamp_seconds=prediction.timestamp_seconds,
                confidence=prediction.confidence,
                ground_truth_event_id=event.id,
                ground_truth_timestamp_seconds=event.timestamp_seconds,
                time_error_seconds=match.time_error_seconds,
                training_decision="include",
            )
        )
    for prediction_index in evaluation.false_positive_prediction_indices:
        prediction = predictions[prediction_index]
        items.append(
            AnalysisPrediction(
                analysis_task_id=task_id,
                outcome="false_positive",
                predicted_timestamp_seconds=prediction.timestamp_seconds,
                confidence=prediction.confidence,
                training_decision="pending",
            )
        )
    for truth_index in evaluation.false_negative_ground_truth_indices:
        event = ground_truth_events[truth_index]
        items.append(
            AnalysisPrediction(
                analysis_task_id=task_id,
                outcome="false_negative",
                ground_truth_event_id=event.id,
                ground_truth_timestamp_seconds=event.timestamp_seconds,
                training_decision="include",
            )
        )
    db.add_all(items)
    db.flush()
    return items


def list_task_predictions(db: Session, task_id: str) -> list[AnalysisPrediction]:
    return list(
        db.scalars(
            select(AnalysisPrediction)
            .where(AnalysisPrediction.analysis_task_id == task_id)
            .order_by(
                AnalysisPrediction.outcome,
                AnalysisPrediction.predicted_timestamp_seconds,
                AnalysisPrediction.ground_truth_timestamp_seconds,
                AnalysisPrediction.id,
            )
        )
    )


def get_prediction(db: Session, prediction_id: int) -> AnalysisPrediction | None:
    return db.get(AnalysisPrediction, prediction_id)


def review_false_positive(
    db: Session,
    *,
    prediction: AnalysisPrediction,
    decision: str,
    user_id: int,
) -> AnalysisPrediction:
    prediction.training_decision = decision
    prediction.reviewed_by_user_id = user_id
    prediction.reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(prediction)
    return prediction
