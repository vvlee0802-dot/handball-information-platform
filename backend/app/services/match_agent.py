from datetime import datetime, timezone
import json
from time import perf_counter
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent import AgentRun, AgentToolCall, ChatMessage, ChatSession
from app.models.match import Match
from app.models.team import Team
from app.models.user import User
from app.schemas.agent import AgentSource
from app.services.agent_tools import (
    AgentToolError,
    AgentToolPermissionError,
    available_tool_schemas,
    execute_agent_tool,
    sanitize_arguments,
    summarize_tool_result,
)


class MatchAgentError(RuntimeError):
    pass


def _system_prompt(db: Session, session: ChatSession) -> str:
    context = "当前会话尚未选择比赛。问题依赖具体比赛时，必须请用户先选择比赛，不得猜测。"
    if session.match_id is not None:
        match = db.get(Match, session.match_id)
        if match is not None:
            home = db.get(Team, match.home_team_id)
            away = db.get(Team, match.away_team_id)
            context = (
                f"当前会话比赛 ID 为 {match.id}，"
                f"{home.name if home else '主队'} 对 {away.name if away else '客队'}。"
                "用户使用‘他们’‘下半场’等指代时，结合本会话历史和这场比赛解析。"
            )
    return (
        "你是手球比赛分析 Agent。事实问题必须先调用提供的工具，不能依赖模型记忆补充比分、"
        "球员、事件或规则。多个数据源的问题应分别调用工具后再整合。工具无数据或失败时，"
        "明确说明限制，不得伪造结果。最终回答使用简洁中文，并说明依据来自比赛信息、官方统计、"
        "已确认事件或知识文档。任何写操作都只能调用 propose 工具形成待确认计划，绝不能声称已经执行。"
        f"{context}"
    )


def _request_model(messages: list[dict], tools: list[dict]) -> dict:
    if not (
        settings.match_report_llm_base_url
        and settings.match_report_llm_api_key
        and settings.match_report_llm_model
    ):
        raise MatchAgentError("尚未配置 Agent 模型。")
    try:
        response = httpx.post(
            f"{settings.match_report_llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.match_report_llm_api_key}"},
            json={
                "model": settings.match_report_llm_model,
                "temperature": 0.1,
                "enable_thinking": False,
                "max_tokens": min(settings.match_report_llm_max_tokens, 2200),
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
            },
            timeout=settings.match_report_llm_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        return {
            "message": body["choices"][0]["message"],
            "usage": body.get("usage", {}),
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise MatchAgentError(f"Agent 模型调用失败：{exc}") from exc


def _history(db: Session, session_id: str) -> list[dict]:
    records = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(max(2, settings.match_agent_history_messages))
        )
    )
    return [
        {"role": message.role, "content": message.content}
        for message in reversed(records)
    ]


def _merge_usage(total: dict, current: dict) -> dict:
    merged = dict(total)
    for key, value in current.items():
        if isinstance(value, int):
            merged[key] = int(merged.get(key, 0)) + value
    return merged


def run_match_agent(
    db: Session,
    *,
    session: ChatSession,
    user: User,
    user_message: ChatMessage,
    retry_of_run_id: str | None = None,
) -> AgentRun:
    started = perf_counter()
    run = AgentRun(
        id=str(uuid4()),
        session_id=session.id,
        user_message_id=user_message.id,
        retry_of_run_id=retry_of_run_id,
        status="running",
        model_name=settings.match_report_llm_model or "unconfigured",
        prompt_version=settings.match_agent_prompt_version,
        token_usage={},
    )
    db.add(run)
    db.flush()
    sources: dict[str, AgentSource] = {}
    usage: dict = {}
    sequence = 0
    messages = [{"role": "system", "content": _system_prompt(db, session)}, *_history(db, session.id)]
    tools = available_tool_schemas(user)

    try:
        for _step in range(max(1, settings.match_agent_max_tool_steps)):
            response = _request_model(messages, tools)
            usage = _merge_usage(usage, response["usage"])
            model_message = response["message"]
            tool_requests = model_message.get("tool_calls") or []
            if not tool_requests:
                content = str(model_message.get("content") or "").strip()
                if not content:
                    raise MatchAgentError("模型没有返回可显示的回答。")
                assistant = ChatMessage(
                    id=str(uuid4()),
                    session_id=session.id,
                    role="assistant",
                    content=content,
                    sources=[source.model_dump(mode="json") for source in sources.values()],
                    created_at=datetime.now(timezone.utc),
                )
                db.add(assistant)
                db.flush()
                run.assistant_message_id = assistant.id
                run.status = "completed"
                run.token_usage = usage
                run.latency_ms = int((perf_counter() - started) * 1000)
                run.completed_at = datetime.now(timezone.utc)
                session.updated_at = run.completed_at
                db.commit()
                db.refresh(run)
                return run

            messages.append(
                {
                    "role": "assistant",
                    "content": model_message.get("content"),
                    "tool_calls": tool_requests,
                }
            )
            for request in tool_requests:
                sequence += 1
                function = request.get("function") or {}
                tool_name = str(function.get("name") or "unknown")
                call_id = str(request.get("id") or f"call-{sequence}")
                raw = function.get("arguments") or "{}"
                try:
                    arguments = json.loads(raw) if isinstance(raw, str) else dict(raw)
                except (TypeError, ValueError):
                    arguments = {"invalid_arguments": str(raw)[:500]}
                record = AgentToolCall(
                    id=f"{run.id}:{sequence}",
                    run_id=run.id,
                    sequence=sequence,
                    tool_name=tool_name,
                    status="running",
                    duration_ms=0,
                    arguments_summary=sanitize_arguments(arguments),
                    retryable=False,
                )
                db.add(record)
                db.flush()
                try:
                    payload, tool_sources, _proposal_id, duration_ms = execute_agent_tool(
                        db,
                        name=tool_name,
                        raw_arguments=arguments,
                        user=user,
                        session=session,
                        run_id=run.id,
                    )
                    for source in tool_sources:
                        sources[source.id] = source
                    record.status = "completed"
                    record.duration_ms = duration_ms
                    record.result_summary = summarize_tool_result(payload, tool_sources)
                    tool_result = {"ok": True, "data": payload}
                except AgentToolError as exc:
                    record.status = "denied" if isinstance(exc, AgentToolPermissionError) else "failed"
                    record.retryable = bool(getattr(exc, "retryable", False))
                    record.error_message = str(exc)[:1000]
                    tool_result = {
                        "ok": False,
                        "error": str(exc),
                        "retryable": record.retryable,
                    }
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": tool_name,
                        "content": json.dumps(tool_result, ensure_ascii=False),
                    }
                )
                db.flush()
        raise MatchAgentError("Agent 达到本次允许的最大工具调用轮数，请缩小问题范围后重试。")
    except MatchAgentError as exc:
        assistant = ChatMessage(
            id=str(uuid4()),
            session_id=session.id,
            role="assistant",
            content=f"本次分析未完成：{exc} 请稍后重试。",
            sources=[source.model_dump(mode="json") for source in sources.values()],
            created_at=datetime.now(timezone.utc),
        )
        db.add(assistant)
        db.flush()
        run.assistant_message_id = assistant.id
        run.status = "failed"
        run.error_type = type(exc).__name__
        run.error_message = str(exc)[:2000]
        run.token_usage = usage
        run.latency_ms = int((perf_counter() - started) * 1000)
        run.completed_at = datetime.now(timezone.utc)
        session.updated_at = run.completed_at
        db.commit()
        db.refresh(run)
        return run
