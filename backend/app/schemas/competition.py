from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CompetitionStatus = Literal["draft", "active", "completed", "archived"]


class CompetitionBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    season: str = Field(min_length=1, max_length=50)
    stage: str | None = Field(default=None, max_length=80)
    status: CompetitionStatus = "draft"

    model_config = ConfigDict(str_strip_whitespace=True)


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    season: str | None = Field(default=None, min_length=1, max_length=50)
    stage: str | None = Field(default=None, max_length=80)
    status: CompetitionStatus | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


class CompetitionRead(CompetitionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
