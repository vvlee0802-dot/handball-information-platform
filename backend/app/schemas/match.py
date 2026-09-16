from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MatchStatus = Literal["scheduled", "live", "completed", "cancelled"]


class MatchBase(BaseModel):
    competition_id: int = Field(gt=0)
    home_team_id: int = Field(gt=0)
    away_team_id: int = Field(gt=0)
    venue_id: int = Field(gt=0)
    match_date: date
    start_time: time
    stage: str = Field(min_length=1, max_length=80)
    status: MatchStatus = "scheduled"
    home_score: int | None = Field(default=None, ge=0)
    away_score: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_match(self) -> "MatchBase":
        if self.home_team_id == self.away_team_id:
            raise ValueError("Home and away teams must be different")
        if (self.home_score is None) != (self.away_score is None):
            raise ValueError("Both scores must be provided together")
        if self.status == "completed" and self.home_score is None:
            raise ValueError("Completed matches require scores")
        return self


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    competition_id: int | None = Field(default=None, gt=0)
    home_team_id: int | None = Field(default=None, gt=0)
    away_team_id: int | None = Field(default=None, gt=0)
    venue_id: int | None = Field(default=None, gt=0)
    match_date: date | None = None
    start_time: time | None = None
    stage: str | None = Field(default=None, min_length=1, max_length=80)
    status: MatchStatus | None = None
    home_score: int | None = Field(default=None, ge=0)
    away_score: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(str_strip_whitespace=True)


class MatchRead(MatchBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
