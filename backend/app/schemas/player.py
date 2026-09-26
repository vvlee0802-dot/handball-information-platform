from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PlayerBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    number: int = Field(ge=0, le=99)
    team_id: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(str_strip_whitespace=True)


class PlayerCreate(PlayerBase):
    position: str = Field(min_length=1, max_length=50)
    birth_date: date


class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    number: int | None = Field(default=None, ge=0, le=99)
    position: str | None = Field(default=None, min_length=1, max_length=50)
    team_id: int | None = Field(default=None, gt=0)
    birth_date: date | None = None
    description: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(str_strip_whitespace=True)


class PlayerRead(PlayerBase):
    position: str | None = None
    birth_date: date | None = None
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
