"""Бизнес-логика мест переселения."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import Location
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.location_repository import LocationRepository
from app.schemas import LocationCreate
from app.services.exceptions import NotFoundError


class LocationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.locations = LocationRepository(session)
        self.assignments = AssignmentRepository(session)

    async def list_locations(self) -> list[Location]:
        return await self.locations.list_all()

    async def create_location(self, payload: LocationCreate) -> Location:
        location = await self.locations.create(payload)
        await self.session.commit()
        logger.info("create_location: создано место «{}» (id={})", location.name, location.id)
        return location

    async def delete_location(self, location_id: int) -> None:
        location = await self.locations.get(location_id)
        if location is None:
            raise NotFoundError("Место переселения не найдено")
        await self.assignments.delete_for_location(location_id)
        await self.locations.delete(location)
        await self.session.commit()
        logger.info("delete_location: удалено место id={}", location_id)
