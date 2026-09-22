"""Формирование итогового отчёта."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.ghost_repository import GhostRepository
from app.repositories.location_repository import LocationRepository
from app.schemas import ReportLocationLoad, ReportOut


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.ghosts = GhostRepository(session)
        self.locations = LocationRepository(session)
        self.assignments = AssignmentRepository(session)

    async def build_report(self) -> ReportOut:
        ghosts = await self.ghosts.list_all()
        locations = await self.locations.list_all()
        assignments = await self.assignments.list_all()

        assigned_ghost_ids = {a.ghost_id for a in assignments}
        unrelocated_ghosts = [g for g in ghosts if g.id not in assigned_ghost_ids]

        most_problematic = [
            {
                "ghost_id": g.id,
                "name": g.name,
                "anxiety_level": g.anxiety_level,
                "deadline": g.relocation_deadline.isoformat(),
            }
            for g in sorted(unrelocated_ghosts, key=lambda g: -g.anxiety_level)[:5]
        ]

        overloaded = [
            ReportLocationLoad(
                location_id=loc.id,
                location_name=loc.name,
                capacity=loc.capacity,
                occupied=loc.occupied,
                load_ratio=round(loc.occupied / loc.capacity, 2) if loc.capacity else 0.0,
            )
            for loc in locations
            if loc.capacity and loc.occupied / loc.capacity >= 0.8
        ]
        overloaded.sort(key=lambda r: -r.load_ratio)

        logger.info(
            "build_report: всего={} расселено={} не расселено={} перегруженных мест={}",
            len(ghosts), len(assigned_ghost_ids), len(unrelocated_ghosts), len(overloaded),
        )

        return ReportOut(
            total_ghosts=len(ghosts),
            relocated=len(assigned_ghost_ids),
            unrelocated=len(unrelocated_ghosts),
            most_problematic=most_problematic,
            overloaded_locations=overloaded,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
