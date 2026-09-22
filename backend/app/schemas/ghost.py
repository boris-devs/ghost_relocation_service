from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.db.enums import SpecialCondition


class GhostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    anxiety_level: int = Field(ge=1, le=10)
    favorite_temperature: float = Field(ge=-30, le=40)
    relocation_deadline: date
    special_conditions: list[SpecialCondition] = Field(default_factory=list)


class GhostOut(GhostCreate):
    id: int

    model_config = {"from_attributes": True}
