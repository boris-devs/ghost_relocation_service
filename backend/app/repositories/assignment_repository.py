from __future__ import annotations

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Assignment


class AssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Assignment]:
        result = await self.session.execute(select(Assignment))
        return list(result.scalars().all())

    async def get_by_ghost(self, ghost_id: int) -> Assignment | None:
        result = await self.session.execute(select(Assignment).where(Assignment.ghost_id == ghost_id))
        return result.scalar_one_or_none()

    def add(self, assignment: Assignment) -> None:
        self.session.add(assignment)

    async def delete(self, assignment: Assignment) -> None:
        await self.session.delete(assignment)

    async def delete_for_ghost(self, ghost_id: int) -> None:
        await self.session.execute(sql_delete(Assignment).where(Assignment.ghost_id == ghost_id))

    async def delete_for_location(self, location_id: int) -> None:
        await self.session.execute(sql_delete(Assignment).where(Assignment.location_id == location_id))
