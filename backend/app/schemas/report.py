from __future__ import annotations

from pydantic import BaseModel


class ReportLocationLoad(BaseModel):
    location_id: int
    location_name: str
    capacity: int
    occupied: int
    load_ratio: float


class ReportOut(BaseModel):
    total_ghosts: int
    relocated: int
    unrelocated: int
    most_problematic: list[dict]
    overloaded_locations: list[ReportLocationLoad]
    generated_at: str
