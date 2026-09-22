from __future__ import annotations

from pydantic import BaseModel, Field

from app.db.enums import Humidity, Lighting


class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location_type: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1)
    occupied: int = Field(default=0, ge=0)
    lighting: Lighting
    noise_level: int = Field(ge=0, le=10)
    humidity: Humidity
    ambient_temperature: float = Field(ge=-30, le=40)
    has_people: bool = False
    has_mirrors: bool = False
    has_attic: bool = False
    restrictions: list[str] = Field(default_factory=list)


class LocationOut(LocationCreate):
    id: int

    model_config = {"from_attributes": True}
