from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


KnowledgeVisibility = Literal["platform", "team_private", "owner_private"]
KnowledgeDocumentStatus = Literal["processing", "ready", "failed"]


class DocumentChunkRead(BaseModel):
    id: int
    ordinal: int
    content: str
    page_number: int | None
    section_title: str | None
    indexed: bool = False

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentRead(BaseModel):
    id: str
    owner_user_id: int
    owner_name: str
    team_id: int | None
    team_name: str | None
    original_filename: str
    content_type: str
    size_bytes: int
    visibility: KnowledgeVisibility
    status: KnowledgeDocumentStatus
    parser_name: str
    page_count: int
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentDetail(KnowledgeDocumentRead):
    chunks: list[DocumentChunkRead]


class KnowledgeQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class KnowledgeCitation(BaseModel):
    chunk_id: int
    document_id: str
    document_name: str
    page_number: int | None
    section_title: str | None
    excerpt: str
    score: float


class KnowledgeAnswer(BaseModel):
    answer: str
    citations: list[KnowledgeCitation]
    insufficient_evidence: bool
    answer_model: str
    embedding_model: str
    prompt_version: str


class RagEvaluationCaseCreate(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    expected_document_ids: list[str] = Field(min_length=1, max_length=20)


class RagEvaluationCaseRead(RagEvaluationCaseCreate):
    id: int
    owner_user_id: int
    team_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RagEvaluationDetail(BaseModel):
    case_id: int
    question: str
    expected_document_ids: list[str]
    retrieved_chunks: list[dict]
    answer: str
    insufficient_evidence: bool
    citation_chunk_ids: list[int]
    citation_document_ids: list[str]
    recall_at_k: float
    citation_hit_rate: float
    ungrounded: bool


class RagEvaluationRunRead(BaseModel):
    id: str
    run_by_user_id: int
    team_id: int | None
    embedding_model: str
    answer_model: str
    prompt_version: str
    top_k: int
    relevance_threshold: float
    case_count: int
    recall_at_k: float
    citation_hit_rate: float
    ungrounded_answer_rate: float
    details: list[RagEvaluationDetail]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
