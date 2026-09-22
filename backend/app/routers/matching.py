from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import ManualAssignRequest, ManualAssignResponse, MatchResultOut
from app.services.exceptions import NotFoundError
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/api/match", tags=["matching"])


@router.get("", response_model=list[MatchResultOut])
async def current_status(db: AsyncSession = Depends(get_db)):
    return await MatchingService(db).current_status()


@router.post("/run", response_model=list[MatchResultOut])
async def run_matching(db: AsyncSession = Depends(get_db)):
    return await MatchingService(db).run_matching()


@router.post("/manual", response_model=ManualAssignResponse)
async def manual_assign(payload: ManualAssignRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await MatchingService(db).manual_assign(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{ghost_id}", status_code=204)
async def unassign(ghost_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await MatchingService(db).unassign(ghost_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
