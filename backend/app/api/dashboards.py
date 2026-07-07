import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.permissions import get_dashboard_role, require_role
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import Dashboard, Chart, DashboardMember
from app.schemas.dashboard import (
    DashboardCreate, DashboardUpdate, DashboardResponse, DashboardListResponse,
    ChartCreate, ChartUpdate, ChartResponse,
    MemberCreate, MemberResponse,
)

router = APIRouter()


# ═══════════════════════════════════════════
# Dashboard CRUD
# ═══════════════════════════════════════════

@router.get("", response_model=list[DashboardListResponse])
@limiter.limit("30/minute")
async def list_dashboards(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户拥有的 + 被邀请为成员的看板，附带角色信息。"""
    # 自己的看板
    own_query = select(Dashboard).where(Dashboard.user_id == current_user.id)
    own_result = await db.execute(own_query)
    own_dashboards = list(own_result.scalars().all())

    # 作为成员的看板
    member_subquery = select(DashboardMember.dashboard_id).where(
        DashboardMember.user_id == current_user.id
    )
    member_query = select(Dashboard).where(Dashboard.id.in_(member_subquery))
    member_result = await db.execute(member_query)
    member_dashboards = list(member_result.scalars().all())

    # 合并去重（使用 id 集合）
    seen_ids = set()
    resp = []
    for d in own_dashboards:
        if d.id in seen_ids:
            continue
        seen_ids.add(d.id)
        count_result = await db.execute(
            select(func.count(Chart.id)).where(Chart.dashboard_id == d.id)
        )
        chart_count = count_result.scalar()
        resp.append(DashboardListResponse(
            id=d.id, name=d.name, description=d.description,
            is_published=d.is_published, created_at=d.created_at, updated_at=d.updated_at,
            chart_count=chart_count, role="owner",
        ))

    for d in member_dashboards:
        if d.id in seen_ids:
            continue
        seen_ids.add(d.id)
        count_result = await db.execute(
            select(func.count(Chart.id)).where(Chart.dashboard_id == d.id)
        )
        chart_count = count_result.scalar()
        # 查询角色
        member = (
            await db.execute(
                select(DashboardMember).where(
                    DashboardMember.dashboard_id == d.id,
                    DashboardMember.user_id == current_user.id,
                )
            )
        ).scalar_one()
        resp.append(DashboardListResponse(
            id=d.id, name=d.name, description=d.description,
            is_published=d.is_published, created_at=d.created_at, updated_at=d.updated_at,
            chart_count=chart_count, role=member.role,
        ))

    # 按更新时间倒序
    resp.sort(key=lambda x: x.updated_at, reverse=True)
    return resp


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_dashboard(
    request: Request,
    data: DashboardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    dashboard = Dashboard(user_id=current_user.id, name=data.name, description=data.description)
    db.add(dashboard)
    await db.commit()
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard.id)
    )
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: int,
    role: str = Depends(require_role("owner", "editor", "viewer")),
    db: AsyncSession = Depends(get_db),
):
    """获取看板详情（需要 owner/editor/viewer 权限）。"""
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    data: DashboardUpdate,
    role: str = Depends(require_role("owner", "editor")),
    db: AsyncSession = Depends(get_db),
):
    """更新看板（需要 owner/editor 权限）。"""
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one()
    if data.name is not None:
        dashboard.name = data.name
    if data.description is not None:
        dashboard.description = data.description
    await db.commit()
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: int,
    role: str = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    """删除看板（仅 owner 可操作）。"""
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one()
    await db.delete(dashboard)
    await db.commit()


@router.post("/{dashboard_id}/publish", response_model=DashboardResponse)
async def publish_dashboard(
    dashboard_id: int,
    role: str = Depends(require_role("owner", "editor")),
    db: AsyncSession = Depends(get_db),
):
    """发布看板（需要 owner/editor 权限）。"""
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one()
    dashboard.is_published = True
    if not dashboard.share_token:
        dashboard.share_token = secrets.token_urlsafe(16)
    await db.commit()
    result = await db.execute(
        select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)


# ═══════════════════════════════════════════
# Charts
# ═══════════════════════════════════════════

@router.get("/{dashboard_id}/charts", response_model=list[ChartResponse])
async def list_charts(
    dashboard_id: int,
    role: str = Depends(require_role("owner", "editor", "viewer")),
    db: AsyncSession = Depends(get_db),
):
    chart_result = await db.execute(
        select(Chart).where(Chart.dashboard_id == dashboard_id).order_by(Chart.sort_order)
    )
    charts = chart_result.scalars().all()
    return [ChartResponse.model_validate(c) for c in charts]


@router.post("/{dashboard_id}/charts", response_model=ChartResponse, status_code=status.HTTP_201_CREATED)
async def create_chart(
    dashboard_id: int,
    data: ChartCreate,
    role: str = Depends(require_role("owner", "editor")),
    db: AsyncSession = Depends(get_db),
):
    """创建图表（需要 owner/editor 权限）。"""
    chart = Chart(
        dashboard_id=dashboard_id, chart_type=data.chart_type, title=data.title,
        position_x=data.position_x, position_y=data.position_y, width=data.width, height=data.height,
        data_source_id=data.data_source_id, config_json=data.config_json, query_config=data.query_config,
        sort_order=data.sort_order
    )
    db.add(chart)
    await db.commit()
    await db.refresh(chart)
    return ChartResponse.model_validate(chart)


@router.put("/charts/{chart_id}", response_model=ChartResponse)
async def update_chart(
    chart_id: int,
    data: ChartUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新图表（需验证对所属看板的 owner/editor 权限）。"""
    result = await db.execute(select(Chart).where(Chart.id == chart_id))
    chart = result.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    # 权限检查：需要是所属看板的 owner 或 editor
    role = await get_dashboard_role(chart.dashboard_id, current_user.id, db)
    if role not in ("owner", "editor"):
        if role is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        raise HTTPException(status_code=403, detail="无权修改此图表")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chart, field, value)
    await db.commit()
    await db.refresh(chart)
    return ChartResponse.model_validate(chart)


@router.delete("/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(
    chart_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除图表（需验证对所属看板的 owner/editor 权限）。"""
    result = await db.execute(select(Chart).where(Chart.id == chart_id))
    chart = result.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    # 权限检查：需要是所属看板的 owner 或 editor
    role = await get_dashboard_role(chart.dashboard_id, current_user.id, db)
    if role not in ("owner", "editor"):
        if role is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        raise HTTPException(status_code=403, detail="无权删除此图表")

    await db.delete(chart)
    await db.commit()


# ═══════════════════════════════════════════
# Members (RBAC)
# ═══════════════════════════════════════════

@router.get("/{dashboard_id}/members", response_model=list[MemberResponse])
async def list_members(
    dashboard_id: int,
    role: str = Depends(require_role("owner", "editor", "viewer")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看成员列表（需要至少 viewer 权限）。"""
    # 加载 owner 信息
    dashboard = (
        await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    ).scalar_one()
    owner = (
        await db.execute(select(User).where(User.id == dashboard.user_id))
    ).scalar_one()

    members = []
    # owner 始终在列表中
    members.append(MemberResponse(
        id=0,  # 特殊标记，owner 没有 DashboardMember 记录
        user_id=owner.id,
        role="owner",
        username=owner.username,
        created_at=dashboard.created_at,
    ))

    # 其他成员
    result = await db.execute(
        select(DashboardMember, User.username).join(User, DashboardMember.user_id == User.id).where(
            DashboardMember.dashboard_id == dashboard_id
        ).order_by(DashboardMember.created_at)
    )
    for member, username in result:
        members.append(MemberResponse(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            username=username,
            created_at=member.created_at,
        ))

    return members


@router.post("/{dashboard_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    dashboard_id: int,
    data: MemberCreate,
    role: str = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    """添加成员（仅 owner 可操作）。"""
    if data.role not in ("editor", "viewer"):
        raise HTTPException(status_code=400, detail="role 必须是 editor 或 viewer")

    # 不能添加自己
    dashboard = (
        await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    ).scalar_one()
    if data.user_id == dashboard.user_id:
        raise HTTPException(status_code=400, detail="不能添加自己为成员")

    # 检查用户是否存在
    user = (
        await db.execute(select(User).where(User.id == data.user_id))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否已是成员
    existing = (
        await db.execute(
            select(DashboardMember).where(
                DashboardMember.dashboard_id == dashboard_id,
                DashboardMember.user_id == data.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已是成员")

    member = DashboardMember(
        dashboard_id=dashboard_id,
        user_id=data.user_id,
        role=data.role,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        username=user.username,
        created_at=member.created_at,
    )


@router.delete("/{dashboard_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    dashboard_id: int,
    user_id: int,
    role: str = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
):
    """移除成员（仅 owner 可操作）。"""
    result = await db.execute(
        select(DashboardMember).where(
            DashboardMember.dashboard_id == dashboard_id,
            DashboardMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    await db.delete(member)
    await db.commit()
