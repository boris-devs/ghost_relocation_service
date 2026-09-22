from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ghost
from app.schemas import GhostCreate


class GhostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Ghost]:
        result = await self.session.execute(select(Ghost).order_by(Ghost.id))
        return list(result.scalars().all())

    async def get(self, ghost_id: int) -> Ghost | None:
        return await self.session.get(Ghost, ghost_id)

    async def create(self, payload: GhostCreate) -> Ghost:
        ghost = Ghost(
            name=payload.name,
            anxiety_level=payload.anxiety_level,
            favorite_temperature=payload.favorite_temperature,
            relocation_deadline=payload.relocation_deadline,
            special_conditions=[c.value for c in payload.special_conditions],
        )
        self.session.add(ghost)
        await self.session.flush()
        await self.session.refresh(ghost)
        return ghost

    async def delete(self, ghost: Ghost) -> None:
        await self.session.delete(ghost)
