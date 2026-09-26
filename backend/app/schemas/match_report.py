from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportPlayer(BaseModel):
    number: int = Field(ge=0, le=99)
    name: str
    goals: int = Field(ge=0)
    yellow_cards: int = Field(ge=0)
    suspensions_2min: int = Field(ge=0)
    red_cards: int = Field(ge=0)
    blue_cards: int = Field(ge=0)


class ReportTeam(BaseModel):
    side: str
    code: str
    name: str
    half_time_score: int = Field(ge=0)
    final_score: int = Field(ge=0)
    seven_meter_goals: int = Field(ge=0)
    seven_meter_attempts: int = Field(ge=0)
    timeouts: list[str]
    players: list[ReportPlayer]


class ParsedMatchReport(BaseModel):
    report_type: str
    match_number: int | None
    competition_stage: str | None
    match_date: str | None
    start_time: str | None
    venue: str | None
    team_a: ReportTeam
    team_b: ReportTeam


class MatchReportPreview(BaseModel):
    id: str
    match_id: int
    original_filename: str
    status: str
    parsed: ParsedMatchReport
    conflicts: list[str]
    suggested_team_a_team_id: int | None
    suggested_team_b_team_id: int | None
    duplicate: bool = False
    created_at: datetime


class MatchReportConfirm(BaseModel):
    team_a_team_id: int = Field(gt=0)
    team_b_team_id: int = Field(gt=0)
    accept_conflicts: bool = False

    @model_validator(mode="after")
    def validate_team_mapping(self) -> "MatchReportConfirm":
        if self.team_a_team_id == self.team_b_team_id:
            raise ValueError("Team A and Team B must map to different teams")
        return self


class OfficialPlayerStatRead(BaseModel):
    id: int
    team_id: int
    player_id: int | None
    player_name: str
    number: int
    goals: int
    yellow_cards: int
    suspensions_2min: int
    red_cards: int
    blue_cards: int

    model_config = ConfigDict(from_attributes=True)


class OfficialTeamStatRead(BaseModel):
    id: int
    team_id: int
    report_side: str
    half_time_score: int
    final_score: int
    seven_meter_goals: int
    seven_meter_attempts: int
    timeouts: list[str]

    model_config = ConfigDict(from_attributes=True)


class MatchReportRead(BaseModel):
    id: str
    match_id: int
    original_filename: str
    status: str
    parsed: ParsedMatchReport
    conflicts: list[str]
    team_a_team_id: int | None
    team_b_team_id: int | None
    player_stats: list[OfficialPlayerStatRead]
    team_stats: list[OfficialTeamStatRead]
    imported_at: datetime | None
    created_at: datetime
