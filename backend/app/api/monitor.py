"""
监控端点 — 健康检查和统计信息
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.user import User
from app.models.dashboard import Dashboard, Chart, DataSource

router = APIRouter()


@router.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """返回系统统计数据。"""
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    dashboards_count = (await db.execute(select(func.count(Dashboard.id)))).scalar() or 0
    charts_count = (await db.execute(select(func.count(Chart.id)))).scalar() or 0
    datasources_count = (await db.execute(select(func.count(DataSource.id)))).scalar() or 0
    return {
        "users": users_count,
        "dashboards": dashboards_count,
        "charts": charts_count,
        "datasources": datasources_count,
    }
