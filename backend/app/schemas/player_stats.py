from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.event import EventRead

PlayerStatsMetric = Literal["goals", "shots", "saves", "turnovers", "fast_breaks"]


class PlayerMatchStatsRead(BaseModel):
    player_id: int
    player_name: str
    player_number: int
    position: str | None
    team_id: int
    team_name: str
    goals: int
    shots: int
    saves: int
    turnovers: int
    fast_breaks: int
    shooting_percentage: float | None


class MatchPlayerStatsRead(BaseModel):
    match_id: int
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_score: int | None
    away_score: int | None
    goal_source: Literal["official_report", "unavailable"]
    official_report_id: str | None
    players: list[PlayerMatchStatsRead]


class PlayerAssignmentBatchUpdate(BaseModel):
    event_ids: list[int] = Field(min_length=1, max_length=100)
    player_id: int = Field(gt=0)


class PlayerAssignmentBatchRead(BaseModel):
    requested_count: int
    affected_count: int
    events: list[EventRead]


class PlayerAssignmentAuditRead(BaseModel):
    id: int
    match_id: int
    event_id: int
    old_player_id: int | None
    old_player_name: str | None
    new_player_id: int
    new_player_name: str
    changed_by_user_id: int
    changed_by_user_name: str
    changed_at: datetime
