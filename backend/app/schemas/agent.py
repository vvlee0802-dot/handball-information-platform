from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    match_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=120)


class ChatSessionRead(BaseModel):
    id: str
    user_id: int
    match_id: int | None
    match_label: str | None
    title: str
    created_at: datetime
    updated_at: datetime


class AgentSource(BaseModel):
    id: str
    source_type: Literal["match", "event", "player_stat", "knowledge"]
    label: str
    match_id: int | None = None
    event_id: int | None = None
    player_id: int | None = None
    document_id: str | None = None
    timestamp_seconds: float | None = None
    excerpt: str | None = None


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatMessageRead(BaseModel):
    id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[AgentSource]
    created_at: datetime


class AgentToolCallRead(BaseModel):
    id: str
    run_id: str
    sequence: int
    tool_name: str
    status: Literal["running", "completed", "failed", "denied"]
    duration_ms: int
    arguments_summary: dict
    result_summary: dict | None
    retryable: bool
    error_message: str | None
    created_at: datetime


class AgentActionProposalRead(BaseModel):
    id: str
    run_id: str
    session_id: str
    match_id: int | None
    action_name: str
    arguments: dict
    summary: str
    status: Literal["pending", "executed", "rejected", "failed"]
    result: dict | None
    created_at: datetime
    executed_at: datetime | None


class AgentRunRead(BaseModel):
    id: str
    session_id: str
    user_message_id: str | None
    assistant_message_id: str | None
    retry_of_run_id: str | None
    status: Literal["running", "completed", "failed"]
    model_name: str
    prompt_version: str
    latency_ms: int | None
    token_usage: dict
    error_type: str | None
    error_message: str | None
    tool_calls: list[AgentToolCallRead]
    proposals: list[AgentActionProposalRead]
    created_at: datetime
    completed_at: datetime | None


class ChatSessionDetail(BaseModel):
    session: ChatSessionRead
    messages: list[ChatMessageRead]
    runs: list[AgentRunRead]


class AgentTurnRead(BaseModel):
    user_message: ChatMessageRead
    assistant_message: ChatMessageRead | None
    run: AgentRunRead
