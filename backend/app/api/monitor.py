"""
监控端点 — 健康检查、统计信息、数据库备份。
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.backup import backup_database, list_backups
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import Dashboard, Chart, DataSource

router = APIRouter()
logger = structlog.get_logger(__name__)


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


@router.post("/api/admin/backup")
async def trigger_backup(current_user: User = Depends(get_current_user)):
    """手动触发数据库备份（需认证）。"""
    try:
        backup_path = backup_database()
        logger.info("手动备份触发", user_id=current_user.id, backup_path=backup_path)
        return {"status": "ok", "backup_path": backup_path}
    except Exception as e:
        logger.error("备份失败", error=str(e))
        raise HTTPException(status_code=500, detail=f"备份失败: {str(e)}")


@router.get("/api/admin/backups")
async def get_backups(current_user: User = Depends(get_current_user)):
    """列出历史备份文件（需认证）。"""
    backups = list_backups()
    return {"backups": backups}
