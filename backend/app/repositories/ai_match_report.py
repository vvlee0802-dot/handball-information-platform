from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_match_report import AiMatchReport, AiReportEvaluation


def get_report(db: Session, report_id: str) -> AiMatchReport | None:
    return db.get(AiMatchReport, report_id)


def latest_report(db: Session, match_id: int) -> AiMatchReport | None:
    return db.scalar(
        select(AiMatchReport)
        .where(AiMatchReport.match_id == match_id)
        .order_by(AiMatchReport.created_at.desc(), AiMatchReport.id.desc())
        .limit(1)
    )


def list_reports(db: Session, match_id: int) -> list[AiMatchReport]:
    return list(
        db.scalars(
            select(AiMatchReport)
            .where(AiMatchReport.match_id == match_id)
            .order_by(AiMatchReport.created_at.desc(), AiMatchReport.id.desc())
        )
    )


def latest_evaluation(db: Session, report_id: str) -> AiReportEvaluation | None:
    return db.scalar(
        select(AiReportEvaluation)
        .where(AiReportEvaluation.report_id == report_id)
        .order_by(AiReportEvaluation.created_at.desc(), AiReportEvaluation.id.desc())
        .limit(1)
    )


def previous_report_evaluation(
    db: Session, *, match_id: int, report_id: str
) -> AiReportEvaluation | None:
    return db.scalar(
        select(AiReportEvaluation)
        .where(
            AiReportEvaluation.match_id == match_id,
            AiReportEvaluation.report_id != report_id,
        )
        .order_by(AiReportEvaluation.created_at.desc(), AiReportEvaluation.id.desc())
        .limit(1)
    )
