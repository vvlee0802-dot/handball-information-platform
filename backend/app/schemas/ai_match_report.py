from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReportFocus = Literal["full_match", "key_phases", "team_comparison", "player_performance"]
ReportDetailLevel = Literal["concise", "detailed"]


class ReportEvidence(BaseModel):
    id: str
    category: str
    label: str
    value: str
    event_id: int | None = None
    timestamp_seconds: float | None = None


class AiReportSection(BaseModel):
    heading: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=4000)
    evidence_ids: list[str] = Field(default_factory=list)


class AiReportContent(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    sections: list[AiReportSection] = Field(min_length=1, max_length=12)
    limitations: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def require_unique_section_headings(self) -> "AiReportContent":
        headings = [section.heading for section in self.sections]
        if len(headings) != len(set(headings)):
            raise ValueError("Report section headings must be unique")
        return self


class AiReportEvidenceBundle(BaseModel):
    match_id: int
    evidence: list[ReportEvidence]
    limitations: list[str]


class AiMatchReportGenerate(BaseModel):
    focus: ReportFocus = "full_match"
    detail_level: ReportDetailLevel = "concise"


class AiMatchReportUpdate(BaseModel):
    report: AiReportContent


class AiReportEvaluationCheck(BaseModel):
    key: str
    label: str
    passed: bool
    detail: str
    evidence_ids: list[str] = Field(default_factory=list)


class AiReportEvaluationRead(BaseModel):
    id: str
    report_id: str
    match_id: int
    model_name: str
    prompt_version: str
    passed: bool
    score: float
    checks: list[AiReportEvaluationCheck]
    previous_evaluation_id: str | None = None
    previous_model_name: str | None = None
    previous_prompt_version: str | None = None
    previous_score: float | None = None
    score_delta: float | None = None
    created_at: datetime


class AiMatchReportRead(BaseModel):
    id: str
    match_id: int
    status: str
    model_name: str
    prompt_version: str
    generation_focus: ReportFocus
    detail_level: ReportDetailLevel
    is_user_edited: bool
    edited_at: datetime | None
    report: AiReportContent
    evidence: list[ReportEvidence]
    latest_evaluation: AiReportEvaluationRead | None = None
    created_at: datetime
