from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import or_, select

from app.api.dependencies.auth import DatabaseSession, ManageKnowledgeBaseUser
from app.core.authorization import UserRole
from app.models.knowledge import RagEvaluationCase, RagEvaluationRun
from app.repositories import knowledge as knowledge_documents
from app.schemas.knowledge import (
    RagEvaluationCaseCreate,
    RagEvaluationCaseRead,
    RagEvaluationRunRead,
)
from app.services.knowledge_evaluation import run_rag_evaluation
from app.services.knowledge_rag import KnowledgeRagError

router = APIRouter(prefix="/api/knowledge", tags=["knowledge evaluations"])


def _is_admin(role: str) -> bool:
    return role in {UserRole.COMPETITION_ADMIN.value, UserRole.SYSTEM_ADMIN.value}


def _case_scope(current_user: ManageKnowledgeBaseUser):
    if _is_admin(current_user.role):
        return True
    if current_user.team_id is None:
        return RagEvaluationCase.owner_user_id == current_user.id
    return or_(
        RagEvaluationCase.owner_user_id == current_user.id,
        RagEvaluationCase.team_id == current_user.team_id,
    )


def _run_scope(current_user: ManageKnowledgeBaseUser):
    if _is_admin(current_user.role):
        return True
    if current_user.team_id is None:
        return RagEvaluationRun.run_by_user_id == current_user.id
    return or_(
        RagEvaluationRun.run_by_user_id == current_user.id,
        RagEvaluationRun.team_id == current_user.team_id,
    )


@router.get("/evaluation-cases", response_model=list[RagEvaluationCaseRead])
def list_evaluation_cases(
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> list[RagEvaluationCase]:
    query = select(RagEvaluationCase).where(_case_scope(current_user))
    return list(db.scalars(query.order_by(RagEvaluationCase.created_at, RagEvaluationCase.id)))


@router.post(
    "/evaluation-cases",
    response_model=RagEvaluationCaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_case(
    payload: RagEvaluationCaseCreate,
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> RagEvaluationCase:
    accessible_documents = knowledge_documents.list_documents(
        db,
        viewer_user_id=current_user.id,
        viewer_team_id=current_user.team_id,
        include_private_from_others=_is_admin(current_user.role),
    )
    accessible_ids = {
        document.id for document in accessible_documents if document.status == "ready"
    }
    requested_ids = list(dict.fromkeys(payload.expected_document_ids))
    if not set(requested_ids).issubset(accessible_ids):
        raise HTTPException(status_code=400, detail="预期来源中包含不存在或无权访问的文档。")
    evaluation_case = RagEvaluationCase(
        question=payload.question.strip(),
        expected_document_ids=requested_ids,
        owner_user_id=current_user.id,
        team_id=current_user.team_id,
    )
    db.add(evaluation_case)
    db.commit()
    db.refresh(evaluation_case)
    return evaluation_case


@router.delete("/evaluation-cases/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation_case(
    case_id: int,
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> Response:
    evaluation_case = db.scalar(
        select(RagEvaluationCase).where(
            RagEvaluationCase.id == case_id,
            _case_scope(current_user),
        )
    )
    if evaluation_case is None:
        raise HTTPException(status_code=404, detail="评测问题不存在。")
    if not _is_admin(current_user.role) and evaluation_case.owner_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有创建者可以删除该评测问题。")
    db.delete(evaluation_case)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/evaluation-runs", response_model=list[RagEvaluationRunRead])
def list_evaluation_runs(
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> list[RagEvaluationRun]:
    query = select(RagEvaluationRun).where(_run_scope(current_user))
    return list(db.scalars(query.order_by(RagEvaluationRun.created_at.desc()).limit(20)))


@router.post("/evaluation-runs", response_model=RagEvaluationRunRead)
def create_evaluation_run(
    db: DatabaseSession,
    current_user: ManageKnowledgeBaseUser,
) -> RagEvaluationRun:
    cases = list(
        db.scalars(
            select(RagEvaluationCase)
            .where(_case_scope(current_user), RagEvaluationCase.is_active.is_(True))
            .order_by(RagEvaluationCase.id)
        )
    )
    if not cases:
        raise HTTPException(status_code=400, detail="请先添加至少一道固定评测问题。")
    documents = [
        document
        for document in knowledge_documents.list_documents(
            db,
            viewer_user_id=current_user.id,
            viewer_team_id=current_user.team_id,
            include_private_from_others=_is_admin(current_user.role),
        )
        if document.status == "ready"
    ]
    if not documents:
        raise HTTPException(status_code=400, detail="没有可用于评测的知识文档。")
    try:
        return run_rag_evaluation(
            db,
            cases=cases,
            documents=documents,
            run_by_user_id=current_user.id,
            team_id=current_user.team_id,
        )
    except KnowledgeRagError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
