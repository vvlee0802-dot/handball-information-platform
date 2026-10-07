from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authorization import Permission, has_permission
from app.core.config import settings
from app.models.agent import AgentActionProposal, ChatSession
from app.models.competition import Competition
from app.models.event import Event
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team
from app.models.user import User
from app.models.venue import Venue
from app.repositories import knowledge as knowledge_documents
from app.repositories import player_stats
from app.schemas.agent import AgentSource
from app.services.knowledge_rag import embed_texts, ensure_chunk_embeddings, rank_chunks


class AgentToolError(RuntimeError):
    retryable = False


class AgentToolPermissionError(AgentToolError):
    pass


class AgentToolTemporaryError(AgentToolError):
    retryable = True


class MatchArgs(BaseModel):
    match_id: int = Field(gt=0)


class EventArgs(MatchArgs):
    event_type: str | None = Field(default=None, max_length=30)
    team_id: int | None = Field(default=None, gt=0)
    player_id: int | None = Field(default=None, gt=0)


class PlayerStatsArgs(MatchArgs):
    team_id: int | None = Field(default=None, gt=0)
    player_id: int | None = Field(default=None, gt=0)


class KnowledgeArgs(BaseModel):
    query: str = Field(min_length=2, max_length=1000)


class MatchStatusProposalArgs(MatchArgs):
    status: Literal["scheduled", "live", "completed", "cancelled"]


TOOL_DEFINITIONS: dict[str, dict] = {
    "get_match_overview": {
        "description": "读取一场比赛的双方球队、赛事、场馆、日期、阶段、状态和比分。",
        "parameters": {
            "type": "object",
            "properties": {"match_id": {"type": "integer"}},
            "required": ["match_id"],
            "additionalProperties": False,
        },
    },
    "get_match_events": {
        "description": "读取一场比赛已人工确认的事件及视频时间点，可按事件、球队或球员筛选。",
        "parameters": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer"},
                "event_type": {"type": ["string", "null"]},
                "team_id": {"type": ["integer", "null"]},
                "player_id": {"type": ["integer", "null"]},
            },
            "required": ["match_id"],
            "additionalProperties": False,
        },
    },
    "get_player_stats": {
        "description": "读取官方赛后统计中的球员进球数据，可按球队或球员筛选。",
        "parameters": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer"},
                "team_id": {"type": ["integer", "null"]},
                "player_id": {"type": ["integer", "null"]},
            },
            "required": ["match_id"],
            "additionalProperties": False,
        },
    },
    "search_handball_knowledge": {
        "description": "检索当前用户有权访问的手球规则或战术知识文档。",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "propose_update_match_status": {
        "description": "只生成修改比赛状态的待确认计划，不直接修改比赛。",
        "parameters": {
            "type": "object",
            "properties": {
                "match_id": {"type": "integer"},
                "status": {
                    "type": "string",
                    "enum": ["scheduled", "live", "completed", "cancelled"],
                },
            },
            "required": ["match_id", "status"],
            "additionalProperties": False,
        },
    },
}


def available_tool_schemas(user: User) -> list[dict]:
    names = ["get_match_overview", "get_match_events", "get_player_stats"]
    if has_permission(user, Permission.QUERY_KNOWLEDGE_BASE):
        names.append("search_handball_knowledge")
    if has_permission(user, Permission.MANAGE_COMPETITION_DATA):
        names.append("propose_update_match_status")
    return [
        {
            "type": "function",
            "function": {"name": name, **TOOL_DEFINITIONS[name]},
        }
        for name in names
    ]


def sanitize_arguments(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***"
            if any(term in key.lower() for term in ("key", "token", "password", "secret"))
            else sanitize_arguments(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_arguments(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def _ensure_session_match(session: ChatSession, match_id: int) -> None:
    if session.match_id is not None and session.match_id != match_id:
        raise AgentToolError("工具参数中的比赛与当前会话选择的比赛不一致。")


def _match_or_error(db: Session, match_id: int) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise AgentToolError("没有找到指定比赛。")
    return match


def _match_overview(db: Session, args: MatchArgs) -> tuple[dict, list[AgentSource]]:
    match = _match_or_error(db, args.match_id)
    home = db.get(Team, match.home_team_id)
    away = db.get(Team, match.away_team_id)
    competition = db.get(Competition, match.competition_id)
    venue = db.get(Venue, match.venue_id)
    result = {
        "match_id": match.id,
        "competition": competition.name if competition else None,
        "home_team": {"id": home.id, "name": home.name} if home else None,
        "away_team": {"id": away.id, "name": away.name} if away else None,
        "match_date": match.match_date.isoformat(),
        "start_time": match.start_time.isoformat(),
        "stage": match.stage,
        "status": match.status,
        "score": {"home": match.home_score, "away": match.away_score},
        "venue": venue.name if venue else None,
    }
    label = f"比赛 #{match.id}：{home.name if home else '主队'} vs {away.name if away else '客队'}"
    return result, [
        AgentSource(id=f"match:{match.id}", source_type="match", label=label, match_id=match.id)
    ]


def _match_events(db: Session, args: EventArgs) -> tuple[dict, list[AgentSource]]:
    _match_or_error(db, args.match_id)
    statement = select(Event).where(
        Event.match_id == args.match_id,
        Event.status == "verified",
        Event.deleted_at.is_(None),
    )
    if args.event_type:
        statement = statement.where(Event.event_type == args.event_type)
    if args.team_id:
        statement = statement.where(Event.team_id == args.team_id)
    if args.player_id:
        statement = statement.where(Event.player_id == args.player_id)
    events = list(db.scalars(statement.order_by(Event.timestamp_seconds, Event.id).limit(100)))
    team_ids = {event.team_id for event in events if event.team_id is not None}
    player_ids = {event.player_id for event in events if event.player_id is not None}
    teams = (
        {team.id: team for team in db.scalars(select(Team).where(Team.id.in_(team_ids)))}
        if team_ids
        else {}
    )
    players = (
        {
            player.id: player
            for player in db.scalars(select(Player).where(Player.id.in_(player_ids)))
        }
        if player_ids
        else {}
    )
    rows = [
        {
            "event_id": event.id,
            "event_type": event.event_type,
            "timestamp_seconds": event.timestamp_seconds,
            "team": teams[event.team_id].name if event.team_id in teams else None,
            "player": players[event.player_id].name if event.player_id in players else None,
            "note": event.note,
        }
        for event in events
    ]
    sources = [
        AgentSource(
            id=f"event:{event.id}",
            source_type="event",
            label=f"{event.event_type} · {int(event.timestamp_seconds) // 60}:{int(event.timestamp_seconds) % 60:02d}",
            match_id=event.match_id,
            event_id=event.id,
            player_id=event.player_id,
            timestamp_seconds=event.timestamp_seconds,
            excerpt=event.note,
        )
        for event in events
    ]
    return {"match_id": args.match_id, "event_count": len(rows), "events": rows}, sources


def _player_stats(db: Session, args: PlayerStatsArgs) -> tuple[dict, list[AgentSource]]:
    match = _match_or_error(db, args.match_id)
    data = player_stats.get_match_player_stats(db, match)
    rows = [
        item
        for item in data.players
        if (args.team_id is None or item.team_id == args.team_id)
        and (args.player_id is None or item.player_id == args.player_id)
    ]
    result_rows = [item.model_dump() for item in rows]
    sources = [
        AgentSource(
            id=f"player-stat:{args.match_id}:{item.player_id}",
            source_type="player_stat",
            label=f"{item.team_name} #{item.player_number} {item.player_name}：{item.goals} 球",
            match_id=args.match_id,
            player_id=item.player_id,
        )
        for item in rows
    ]
    return {
        "match_id": args.match_id,
        "goal_source": data.goal_source,
        "players": result_rows,
    }, sources


def _knowledge(db: Session, args: KnowledgeArgs, user: User) -> tuple[dict, list[AgentSource]]:
    documents = [
        document
        for document in knowledge_documents.list_documents(
            db,
            viewer_user_id=user.id,
            viewer_team_id=user.team_id,
            include_private_from_others=user.role in {"competition_admin", "system_admin"},
        )
        if document.status == "ready"
    ]
    chunks = [chunk for document in documents for chunk in document.chunks]
    if not chunks:
        return {"query": args.query, "matches": []}, []
    try:
        ensure_chunk_embeddings(db, chunks)
        query_vector = embed_texts([args.query])[0]
    except Exception as exc:
        raise AgentToolTemporaryError(f"知识库检索暂时失败：{exc}") from exc
    ranked = rank_chunks(chunks, query_vector, top_k=max(1, settings.knowledge_retrieval_top_k))
    document_map = {document.id: document for document in documents}
    matches = []
    sources = []
    for chunk, score in ranked:
        if score < settings.knowledge_relevance_threshold:
            continue
        document = document_map[chunk.document_id]
        matches.append(
            {
                "chunk_id": chunk.id,
                "document": document.original_filename,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "content": chunk.content,
                "score": round(score, 4),
            }
        )
        sources.append(
            AgentSource(
                id=f"knowledge:{chunk.id}",
                source_type="knowledge",
                label=f"{document.original_filename} · {chunk.section_title or ('第 ' + str(chunk.page_number) + ' 页' if chunk.page_number else '文本分块')}",
                document_id=document.id,
                excerpt=chunk.content[:500],
            )
        )
    return {"query": args.query, "matches": matches}, sources


def execute_agent_tool(
    db: Session,
    *,
    name: str,
    raw_arguments: dict,
    user: User,
    session: ChatSession,
    run_id: str,
) -> tuple[dict, list[AgentSource], str | None, int]:
    started = perf_counter()
    try:
        if name == "get_match_overview":
            args = MatchArgs.model_validate(raw_arguments)
            _ensure_session_match(session, args.match_id)
            payload, sources = _match_overview(db, args)
            proposal_id = None
        elif name == "get_match_events":
            if not has_permission(user, Permission.VIEW_AUTHORIZED_VIDEO):
                raise AgentToolPermissionError("当前账号没有查看比赛事件的权限。")
            args = EventArgs.model_validate(raw_arguments)
            _ensure_session_match(session, args.match_id)
            payload, sources = _match_events(db, args)
            proposal_id = None
        elif name == "get_player_stats":
            if not has_permission(user, Permission.VIEW_AUTHORIZED_VIDEO):
                raise AgentToolPermissionError("当前账号没有查看球员统计的权限。")
            args = PlayerStatsArgs.model_validate(raw_arguments)
            _ensure_session_match(session, args.match_id)
            payload, sources = _player_stats(db, args)
            proposal_id = None
        elif name == "search_handball_knowledge":
            if not has_permission(user, Permission.QUERY_KNOWLEDGE_BASE):
                raise AgentToolPermissionError("当前账号没有检索知识库的权限。")
            args = KnowledgeArgs.model_validate(raw_arguments)
            payload, sources = _knowledge(db, args, user)
            proposal_id = None
        elif name == "propose_update_match_status":
            if not has_permission(user, Permission.MANAGE_COMPETITION_DATA):
                raise AgentToolPermissionError("当前账号没有修改比赛数据的权限。")
            args = MatchStatusProposalArgs.model_validate(raw_arguments)
            _ensure_session_match(session, args.match_id)
            match = _match_or_error(db, args.match_id)
            proposal = AgentActionProposal(
                id=str(uuid4()),
                run_id=run_id,
                session_id=session.id,
                match_id=match.id,
                action_name="update_match_status",
                arguments={"match_id": match.id, "status": args.status},
                summary=f"将比赛 #{match.id} 的状态从 {match.status} 修改为 {args.status}",
                status="pending",
                requested_by_user_id=user.id,
            )
            db.add(proposal)
            db.flush()
            payload = {
                "proposal_id": proposal.id,
                "status": "pending_confirmation",
                "summary": proposal.summary,
                "executed": False,
            }
            sources = []
            proposal_id = proposal.id
        else:
            raise AgentToolPermissionError(f"工具 {name} 不在允许列表中。")
    except ValidationError as exc:
        raise AgentToolError(f"工具参数无效：{exc.errors()[0]['msg']}") from exc
    duration_ms = int((perf_counter() - started) * 1000)
    return payload, sources, proposal_id, duration_ms


def summarize_tool_result(payload: dict, sources: list[AgentSource]) -> dict:
    summary = {"source_count": len(sources)}
    for key in ("match_id", "event_count", "goal_source", "proposal_id", "status", "executed"):
        if key in payload:
            summary[key] = payload[key]
    if "players" in payload:
        summary["player_count"] = len(payload["players"])
    if "matches" in payload:
        summary["match_count"] = len(payload["matches"])
    return summary
