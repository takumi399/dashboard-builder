"""
权限检查模块 — RBAC 角色验证

提供 get_dashboard_role() 查询用户在看板中的角色，
以及 require_role() 工厂函数生成 FastAPI 依赖注入。
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import Dashboard, DashboardMember


async def get_dashboard_role(dashboard_id: int, user_id: int, db: AsyncSession) -> str | None:
    """获取用户在看板中的角色。owner 返回 'owner'，成员返回角色名，否则 None。"""
    dashboard = (
        await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    ).scalar_one_or_none()
    if not dashboard:
        return None
    if dashboard.user_id == user_id:
        return "owner"
    member = (
        await db.execute(
            select(DashboardMember).where(
                DashboardMember.dashboard_id == dashboard_id,
                DashboardMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    return member.role if member else None


def require_role(*roles: str):
    """依赖工厂：用户必须是指定角色之一才能访问。

    用法:
        @router.post("/{dashboard_id}/charts")
        async def create_chart(
            dashboard_id: int,
            role: str = Depends(require_role("owner", "editor")),
            ...
        ):
    """

    async def dependency(
        dashboard_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> str:
        role = await get_dashboard_role(dashboard_id, current_user.id, db)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="看板不存在",
            )
        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此看板",
            )
        return role

    return dependency
