"""Бизнес-логика заявок привидений: собирает репозитории, решает, что делать,
и владеет границей транзакции (commit)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import Ghost
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.ghost_repository import GhostRepository
from app.schemas import GhostCreate
from app.services.exceptions import NotFoundError


class GhostService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ghosts = GhostRepository(session)
        self.assignments = AssignmentRepository(session)

    async def list_ghosts(self) -> list[Ghost]:
        return await self.ghosts.list_all()

    async def create_ghost(self, payload: GhostCreate) -> Ghost:
        ghost = await self.ghosts.create(payload)
        await self.session.commit()
        logger.info("create_ghost: создана заявка «{}» (id={})", ghost.name, ghost.id)
        return ghost

    async def delete_ghost(self, ghost_id: int) -> None:
        ghost = await self.ghosts.get(ghost_id)
        if ghost is None:
            raise NotFoundError("Заявка привидения не найдена")
        await self.assignments.delete_for_ghost(ghost_id)
        await self.ghosts.delete(ghost)
        await self.session.commit()
        logger.info("delete_ghost: удалена заявка id={}", ghost_id)
