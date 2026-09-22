from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import LocationCreate, LocationOut
from app.services.exceptions import NotFoundError
from app.services.location_service import LocationService

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationOut])
async def list_locations(db: AsyncSession = Depends(get_db)):
    return await LocationService(db).list_locations()


@router.post("", response_model=LocationOut, status_code=201)
async def create_location(payload: LocationCreate, db: AsyncSession = Depends(get_db)):
    return await LocationService(db).create_location(payload)


@router.delete("/{location_id}", status_code=204)
async def delete_location(location_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await LocationService(db).delete_location(location_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
