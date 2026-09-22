from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import ReportOut
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("", response_model=ReportOut)
async def get_report(db: AsyncSession = Depends(get_db)):
    return await ReportService(db).build_report()
