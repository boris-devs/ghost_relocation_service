from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location
from app.schemas import LocationCreate


class LocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Location]:
        result = await self.session.execute(select(Location).order_by(Location.id))
        return list(result.scalars().all())

    async def get(self, location_id: int) -> Location | None:
        return await self.session.get(Location, location_id)

    async def create(self, payload: LocationCreate) -> Location:
        location = Location(
            name=payload.name,
            location_type=payload.location_type,
            capacity=payload.capacity,
            occupied=payload.occupied,
            lighting=payload.lighting.value,
            noise_level=payload.noise_level,
            humidity=payload.humidity.value,
            ambient_temperature=payload.ambient_temperature,
            has_people=payload.has_people,
            has_mirrors=payload.has_mirrors,
            has_attic=payload.has_attic,
            restrictions=payload.restrictions,
        )
        self.session.add(location)
        await self.session.flush()
        await self.session.refresh(location)
        return location

    async def delete(self, location: Location) -> None:
        await self.session.delete(location)
