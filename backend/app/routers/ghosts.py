from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import GhostCreate, GhostOut
from app.services.exceptions import NotFoundError
from app.services.ghost_service import GhostService

router = APIRouter(prefix="/api/ghosts", tags=["ghosts"])


@router.get("", response_model=list[GhostOut])
async def list_ghosts(db: AsyncSession = Depends(get_db)):
    return await GhostService(db).list_ghosts()


@router.post("", response_model=GhostOut, status_code=201)
async def create_ghost(payload: GhostCreate, db: AsyncSession = Depends(get_db)):
    return await GhostService(db).create_ghost(payload)


@router.delete("/{ghost_id}", status_code=204)
async def delete_ghost(ghost_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await GhostService(db).delete_ghost(ghost_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
