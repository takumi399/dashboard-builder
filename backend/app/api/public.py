from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.dashboard import Dashboard
from app.schemas.dashboard import DashboardResponse

router = APIRouter()

@router.get("/dashboards/{token}", response_model=DashboardResponse)
async def get_public_dashboard(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.share_token == token, Dashboard.is_published == True))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found or not published")
    return DashboardResponse.model_validate(dashboard)
