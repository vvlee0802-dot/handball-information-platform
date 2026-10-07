from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import case, delete, select, update

from app.api.dependencies.auth import DatabaseSession, ManageCompetitionDataUser, UseMatchAgentUser
from app.models.agent import (
    AgentActionAudit,
    AgentActionProposal,
    AgentRun,
    AgentToolCall,
    ChatMessage,
    ChatSession,
)
from app.models.match import Match
from app.models.team import Team
from app.schemas.agent import (
    AgentActionProposalRead,
    AgentRunRead,
    AgentToolCallRead,
    AgentTurnRead,
    ChatMessageCreate,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionRead,
)
from app.services.match_agent import run_match_agent

router = APIRouter(prefix="/api/agent", tags=["match analysis agent"])


def _session_or_404(db: DatabaseSession, session_id: str, user_id: int) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Agent session not found")
    return session


def _session_read(db: DatabaseSession, session: ChatSession) -> ChatSessionRead:
    label = None
    if session.match_id is not None:
        match = db.get(Match, session.match_id)
        if match is not None:
            home = db.get(Team, match.home_team_id)
            away = db.get(Team, match.away_team_id)
            label = f"{home.name if home else '主队'} vs {away.name if away else '客队'}"
    return ChatSessionRead(
        id=session.id,
        user_id=session.user_id,
        match_id=session.match_id,
        match_label=label,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _message_read(message: ChatMessage) -> ChatMessageRead:
    return ChatMessageRead(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        sources=message.sources,
        created_at=message.created_at,
    )


def _proposal_read(proposal: AgentActionProposal) -> AgentActionProposalRead:
    return AgentActionProposalRead(
        id=proposal.id,
        run_id=proposal.run_id,
        session_id=proposal.session_id,
        match_id=proposal.match_id,
        action_name=proposal.action_name,
        arguments=proposal.arguments,
        summary=proposal.summary,
        status=proposal.status,
        result=proposal.result,
        created_at=proposal.created_at,
        executed_at=proposal.executed_at,
    )


def _run_read(db: DatabaseSession, run: AgentRun) -> AgentRunRead:
    calls = list(
        db.scalars(
            select(AgentToolCall)
            .where(AgentToolCall.run_id == run.id)
            .order_by(AgentToolCall.sequence)
        )
    )
    proposals = list(
        db.scalars(
            select(AgentActionProposal)
            .where(AgentActionProposal.run_id == run.id)
            .order_by(AgentActionProposal.created_at)
        )
    )
    return AgentRunRead(
        id=run.id,
        session_id=run.session_id,
        user_message_id=run.user_message_id,
        assistant_message_id=run.assistant_message_id,
        retry_of_run_id=run.retry_of_run_id,
        status=run.status,
        model_name=run.model_name,
        prompt_version=run.prompt_version,
        latency_ms=run.latency_ms,
        token_usage=run.token_usage,
        error_type=run.error_type,
        error_message=run.error_message,
        tool_calls=[AgentToolCallRead.model_validate(call, from_attributes=True) for call in calls],
        proposals=[_proposal_read(proposal) for proposal in proposals],
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


def _session_detail(db: DatabaseSession, session: ChatSession) -> ChatSessionDetail:
    messages = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(
                ChatMessage.created_at,
                case((ChatMessage.role == "user", 0), else_=1),
                ChatMessage.id,
            )
        )
    )
    runs = list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.session_id == session.id)
            .order_by(AgentRun.created_at, AgentRun.id)
        )
    )
    return ChatSessionDetail(
        session=_session_read(db, session),
        messages=[_message_read(message) for message in messages],
        runs=[_run_read(db, run) for run in runs],
    )


@router.get("/sessions", response_model=list[ChatSessionRead])
def list_agent_sessions(
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> list[ChatSessionRead]:
    sessions = list(
        db.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        )
    )
    return [_session_read(db, session) for session in sessions]


@router.post("/sessions", response_model=ChatSessionDetail, status_code=201)
def create_agent_session(
    payload: ChatSessionCreate,
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> ChatSessionDetail:
    if payload.match_id is not None and db.get(Match, payload.match_id) is None:
        raise HTTPException(status_code=422, detail="选择的比赛不存在。")
    session = ChatSession(
        id=str(uuid4()),
        user_id=current_user.id,
        match_id=payload.match_id,
        title=payload.title or "新比赛分析",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_detail(db, session)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_agent_session(
    session_id: str,
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> ChatSessionDetail:
    return _session_detail(db, _session_or_404(db, session_id, current_user.id))


@router.delete("/sessions/{session_id}", status_code=204)
def delete_agent_session(
    session_id: str,
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> Response:
    session = _session_or_404(db, session_id, current_user.id)
    run_ids = select(AgentRun.id).where(AgentRun.session_id == session.id)
    proposal_ids = select(AgentActionProposal.id).where(
        AgentActionProposal.session_id == session.id
    )
    db.execute(
        update(AgentActionAudit)
        .where(AgentActionAudit.session_id == session.id)
        .values(session_id=None)
    )
    db.execute(
        update(AgentActionAudit)
        .where(AgentActionAudit.proposal_id.in_(proposal_ids))
        .values(proposal_id=None)
    )
    db.execute(delete(AgentToolCall).where(AgentToolCall.run_id.in_(run_ids)))
    db.execute(delete(AgentActionProposal).where(AgentActionProposal.session_id == session.id))
    db.execute(delete(AgentRun).where(AgentRun.session_id == session.id))
    db.execute(delete(ChatMessage).where(ChatMessage.session_id == session.id))
    db.delete(session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/messages", response_model=AgentTurnRead)
def send_agent_message(
    session_id: str,
    payload: ChatMessageCreate,
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> AgentTurnRead:
    session = _session_or_404(db, session_id, current_user.id)
    message = ChatMessage(
        id=str(uuid4()),
        session_id=session.id,
        role="user",
        content=payload.content.strip(),
        sources=[],
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)
    if session.title == "新比赛分析":
        session.title = payload.content.strip()[:120]
    db.flush()
    run = run_match_agent(db, session=session, user=current_user, user_message=message)
    assistant = db.get(ChatMessage, run.assistant_message_id) if run.assistant_message_id else None
    return AgentTurnRead(
        user_message=_message_read(message),
        assistant_message=_message_read(assistant) if assistant else None,
        run=_run_read(db, run),
    )


@router.post("/runs/{run_id}/retry", response_model=AgentTurnRead)
def retry_agent_run(
    run_id: str,
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> AgentTurnRead:
    previous = db.get(AgentRun, run_id)
    if previous is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    session = _session_or_404(db, previous.session_id, current_user.id)
    if previous.status != "failed" or previous.user_message_id is None:
        raise HTTPException(status_code=409, detail="只有失败的 Agent 运行可以重试。")
    message = db.get(ChatMessage, previous.user_message_id)
    if message is None:
        raise HTTPException(status_code=409, detail="原始问题已经不存在。")
    run = run_match_agent(
        db,
        session=session,
        user=current_user,
        user_message=message,
        retry_of_run_id=previous.id,
    )
    assistant = db.get(ChatMessage, run.assistant_message_id) if run.assistant_message_id else None
    return AgentTurnRead(
        user_message=_message_read(message),
        assistant_message=_message_read(assistant) if assistant else None,
        run=_run_read(db, run),
    )


@router.post("/proposals/{proposal_id}/confirm", response_model=AgentActionProposalRead)
def confirm_agent_proposal(
    proposal_id: str,
    db: DatabaseSession,
    current_user: ManageCompetitionDataUser,
) -> AgentActionProposalRead:
    proposal = db.get(AgentActionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Agent proposal not found")
    session = _session_or_404(db, proposal.session_id, current_user.id)
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="该计划已经处理。")
    if proposal.action_name != "update_match_status" or proposal.match_id is None:
        raise HTTPException(status_code=422, detail="不支持的写操作。")
    match = db.get(Match, proposal.match_id)
    if match is None:
        raise HTTPException(status_code=409, detail="目标比赛已经不存在。")
    new_status = proposal.arguments.get("status")
    if new_status not in {"scheduled", "live", "completed", "cancelled"}:
        raise HTTPException(status_code=422, detail="比赛状态无效。")
    if new_status == "completed" and (match.home_score is None or match.away_score is None):
        raise HTTPException(status_code=409, detail="完赛状态需要先填写双方比分。")
    before = {"match_id": match.id, "status": match.status}
    match.status = new_status
    after = {"match_id": match.id, "status": match.status}
    proposal.status = "executed"
    proposal.confirmed_by_user_id = current_user.id
    proposal.executed_at = datetime.now(timezone.utc)
    proposal.result = after
    db.add(
        AgentActionAudit(
            proposal_id=proposal.id,
            session_id=session.id,
            action_name=proposal.action_name,
            executed_by_user_id=current_user.id,
            before_data=before,
            after_data=after,
        )
    )
    db.commit()
    db.refresh(proposal)
    return _proposal_read(proposal)


@router.post("/proposals/{proposal_id}/reject", response_model=AgentActionProposalRead)
def reject_agent_proposal(
    proposal_id: str,
    db: DatabaseSession,
    current_user: UseMatchAgentUser,
) -> AgentActionProposalRead:
    proposal = db.get(AgentActionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Agent proposal not found")
    _session_or_404(db, proposal.session_id, current_user.id)
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="该计划已经处理。")
    proposal.status = "rejected"
    proposal.confirmed_by_user_id = current_user.id
    proposal.executed_at = datetime.now(timezone.utc)
    proposal.result = {"executed": False}
    db.commit()
    db.refresh(proposal)
    return _proposal_read(proposal)
