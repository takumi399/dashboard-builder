import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import Dashboard, Chart
from app.schemas.dashboard import (
    DashboardCreate, DashboardUpdate, DashboardResponse, DashboardListResponse,
    ChartCreate, ChartUpdate, ChartResponse
)

router = APIRouter()

@router.get("", response_model=list[DashboardListResponse])
async def list_dashboards(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Dashboard).where(Dashboard.user_id == current_user.id).order_by(Dashboard.updated_at.desc())
    )
    dashboards = result.scalars().all()
    resp = []
    for d in dashboards:
        count_result = await db.execute(select(func.count(Chart.id)).where(Chart.dashboard_id == d.id))
        chart_count = count_result.scalar()
        resp.append(DashboardListResponse(
            id=d.id, name=d.name, description=d.description,
            is_published=d.is_published, created_at=d.created_at, updated_at=d.updated_at,
            chart_count=chart_count
        ))
    return resp

@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(data: DashboardCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    dashboard = Dashboard(user_id=current_user.id, name=data.name, description=data.description)
    db.add(dashboard)
    await db.commit()
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard.id))
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)

@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(dashboard_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return DashboardResponse.model_validate(dashboard)

@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(dashboard_id: int, data: DashboardUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    if data.name is not None: dashboard.name = data.name
    if data.description is not None: dashboard.description = data.description
    await db.commit()
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)

@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(dashboard_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    await db.delete(dashboard)
    await db.commit()

@router.post("/{dashboard_id}/publish", response_model=DashboardResponse)
async def publish_dashboard(dashboard_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    dashboard.is_published = True
    if not dashboard.share_token:
        dashboard.share_token = secrets.token_urlsafe(16)
    await db.commit()
    result = await db.execute(select(Dashboard).options(selectinload(Dashboard.charts)).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    dashboard = result.scalar_one()
    return DashboardResponse.model_validate(dashboard)

@router.get("/{dashboard_id}/charts", response_model=list[ChartResponse])
async def list_charts(dashboard_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    chart_result = await db.execute(select(Chart).where(Chart.dashboard_id == dashboard_id).order_by(Chart.sort_order))
    charts = chart_result.scalars().all()
    return [ChartResponse.model_validate(c) for c in charts]

@router.post("/{dashboard_id}/charts", response_model=ChartResponse, status_code=status.HTTP_201_CREATED)
async def create_chart(dashboard_id: int, data: ChartCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id, Dashboard.user_id == current_user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Dashboard not found")
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
async def update_chart(chart_id: int, data: ChartUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chart).where(Chart.id == chart_id))
    chart = result.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(chart, field, value)
    await db.commit()
    await db.refresh(chart)
    return ChartResponse.model_validate(chart)

@router.delete("/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(chart_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chart).where(Chart.id == chart_id))
    chart = result.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    await db.delete(chart)
    await db.commit()
