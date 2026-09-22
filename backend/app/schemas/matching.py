from __future__ import annotations

from pydantic import BaseModel, Field


class AssignmentOut(BaseModel):
    location_id: int
    location_name: str
    score: float
    explanation: list[str]
    manual: bool
    warnings: list[str] = Field(default_factory=list)


class MatchResultOut(BaseModel):
    ghost_id: int
    ghost_name: str
    status: str
    assigned: bool = False
    assignment: AssignmentOut | None = None
    impossible_reason: str | None = None
    rejected_locations: list[dict] = Field(default_factory=list)


class ManualAssignRequest(BaseModel):
    ghost_id: int
    location_id: int
    force: bool = False


class ManualAssignResponse(BaseModel):
    status: str  
    assignment: AssignmentOut | None = None
    hard_conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
