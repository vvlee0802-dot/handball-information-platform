from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import ManageMatchReportUser, ViewAuthorizedVideoUser
from app.core.config import settings
from app.db.session import get_db
from app.models.ai_match_report import AiMatchReport, AiReportEvaluation
from app.repositories import ai_match_report as ai_reports
from app.repositories import match as matches
from app.schemas.ai_match_report import (
    AiMatchReportGenerate,
    AiMatchReportRead,
    AiMatchReportUpdate,
    AiReportContent,
    AiReportEvaluationCheck,
    AiReportEvaluationRead,
    AiReportEvidenceBundle,
    ReportEvidence,
)
from app.services.ai_match_report import (
    MatchReportGenerationError,
    build_evidence_bundle,
    evaluate_report,
    generate_report,
)

router = APIRouter(prefix="/api/matches/{match_id}/ai-reports", tags=["ai-match-reports"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _evaluation_read(db: Session, evaluation: AiReportEvaluation) -> AiReportEvaluationRead:
    previous = ai_reports.previous_report_evaluation(
        db,
        match_id=evaluation.match_id,
        report_id=evaluation.report_id,
    )
    return AiReportEvaluationRead(
        id=evaluation.id,
        report_id=evaluation.report_id,
        match_id=evaluation.match_id,
        model_name=evaluation.model_name,
        prompt_version=evaluation.prompt_version,
        passed=evaluation.passed,
        score=evaluation.score,
        checks=[AiReportEvaluationCheck.model_validate(item) for item in evaluation.checks],
        previous_evaluation_id=previous.id if previous else None,
        previous_model_name=previous.model_name if previous else None,
        previous_prompt_version=previous.prompt_version if previous else None,
        previous_score=previous.score if previous else None,
        score_delta=round(evaluation.score - previous.score, 1) if previous else None,
        created_at=evaluation.created_at,
    )


def _read(db: Session, report: AiMatchReport) -> AiMatchReportRead:
    evaluation = ai_reports.latest_evaluation(db, report.id)
    return AiMatchReportRead(
        id=report.id,
        match_id=report.match_id,
        status=report.status,
        model_name=report.model_name,
        prompt_version=report.prompt_version,
        generation_focus=report.generation_focus,
        detail_level=report.detail_level,
        is_user_edited=report.user_output_data is not None,
        edited_at=report.edited_at,
        report=AiReportContent.model_validate(report.user_output_data or report.output_data),
        evidence=[ReportEvidence.model_validate(item) for item in report.evidence],
        latest_evaluation=_evaluation_read(db, evaluation) if evaluation else None,
        created_at=report.created_at,
    )


@router.get("/evidence", response_model=AiReportEvidenceBundle)
def read_report_evidence(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> AiReportEvidenceBundle:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        _snapshot, evidence, limitations = build_evidence_bundle(db, match)
    except MatchReportGenerationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return AiReportEvidenceBundle(match_id=match.id, evidence=evidence, limitations=limitations)


@router.get("/latest", response_model=AiMatchReportRead | None)
def read_latest_ai_report(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> AiMatchReportRead | None:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    report = ai_reports.latest_report(db, match_id)
    return _read(db, report) if report else None


@router.get("", response_model=list[AiMatchReportRead])
def list_ai_reports(
    match_id: int,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> list[AiMatchReportRead]:
    if matches.get_match(db, match_id) is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return [_read(db, report) for report in ai_reports.list_reports(db, match_id)]


@router.post("", response_model=AiMatchReportRead, status_code=201)
def create_ai_report(
    match_id: int,
    payload: AiMatchReportGenerate,
    db: DatabaseSession,
    current_user: ManageMatchReportUser,
) -> AiMatchReportRead:
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    try:
        snapshot, evidence, _limitations = build_evidence_bundle(db, match)
        content, raw = generate_report(
            snapshot,
            valid_evidence_ids={item.id for item in evidence},
            focus=payload.focus,
            detail_level=payload.detail_level,
        )
    except MatchReportGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    report = AiMatchReport(
        id=str(uuid4()),
        match_id=match_id,
        generated_by_user_id=current_user.id,
        status="completed",
        model_name=settings.match_report_llm_model,
        prompt_version=settings.match_report_prompt_version,
        generation_focus=payload.focus,
        detail_level=payload.detail_level,
        input_snapshot=snapshot,
        evidence=[item.model_dump(mode="json") for item in evidence],
        output_data=content.model_dump(mode="json"),
        raw_response=raw,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _read(db, report)


@router.patch("/{report_id}", response_model=AiMatchReportRead)
def update_ai_report(
    match_id: int,
    report_id: str,
    payload: AiMatchReportUpdate,
    db: DatabaseSession,
    current_user: ManageMatchReportUser,
) -> AiMatchReportRead:
    report = ai_reports.get_report(db, report_id)
    if report is None or report.match_id != match_id:
        raise HTTPException(status_code=404, detail="AI report not found")
    valid_ids = {item["id"] for item in report.evidence}
    unknown_ids = {
        evidence_id
        for section in payload.report.sections
        for evidence_id in section.evidence_ids
        if evidence_id not in valid_ids
    }
    if unknown_ids:
        raise HTTPException(
            status_code=422,
            detail=f"编辑内容引用了无效证据：{', '.join(sorted(unknown_ids))}",
        )
    report.user_output_data = payload.report.model_dump(mode="json")
    report.edited_by_user_id = current_user.id
    report.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return _read(db, report)


@router.post(
    "/{report_id}/evaluations",
    response_model=AiReportEvaluationRead,
    status_code=201,
)
def evaluate_ai_report(
    match_id: int,
    report_id: str,
    db: DatabaseSession,
    current_user: ManageMatchReportUser,
) -> AiReportEvaluationRead:
    report = ai_reports.get_report(db, report_id)
    match = matches.get_match(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    if report is None or report.match_id != match_id:
        raise HTTPException(status_code=404, detail="AI report not found")
    try:
        _snapshot, current_evidence, _limitations = build_evidence_bundle(db, match)
    except MatchReportGenerationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    checks, score, passed = evaluate_report(report, current_evidence=current_evidence)
    evaluation = AiReportEvaluation(
        id=str(uuid4()),
        report_id=report.id,
        match_id=match_id,
        evaluated_by_user_id=current_user.id,
        model_name=report.model_name,
        prompt_version=report.prompt_version,
        passed=passed,
        score=score,
        checks=[check.model_dump(mode="json") for check in checks],
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return _evaluation_read(db, evaluation)


@router.get(
    "/{report_id}/evaluations/latest",
    response_model=AiReportEvaluationRead | None,
)
def read_latest_ai_report_evaluation(
    match_id: int,
    report_id: str,
    db: DatabaseSession,
    _current_user: ViewAuthorizedVideoUser,
) -> AiReportEvaluationRead | None:
    report = ai_reports.get_report(db, report_id)
    if report is None or report.match_id != match_id:
        raise HTTPException(status_code=404, detail="AI report not found")
    evaluation = ai_reports.latest_evaluation(db, report_id)
    return _evaluation_read(db, evaluation) if evaluation else None
