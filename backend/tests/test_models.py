"""测试模型：User, Dashboard, Chart, DataSource 的基本字段。"""

import pytest

from app.models.user import User
from app.models.dashboard import Dashboard, Chart, DataSource
from app.core.security import get_password_hash


@pytest.mark.asyncio
async def test_create_user(db_session):
    """创建用户，验证 email/username/password_hash。"""
    user = User(
        username="john",
        email="john@example.com",
        password_hash=get_password_hash("secret123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == "john"
    assert user.email == "john@example.com"
    # 密码应该是哈希过的，不是明文
    assert user.password_hash != "secret123"
    assert user.password_hash.startswith("$2b$")


@pytest.mark.asyncio
async def test_create_dashboard(db_session):
    """创建看板，验证 user_id 关联、默认值。"""
    # 先创建用户
    user = User(
        username="owner",
        email="owner@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    dashboard = Dashboard(
        user_id=user.id,
        name="My Dashboard",
        description="A test dashboard",
    )
    db_session.add(dashboard)
    await db_session.commit()
    await db_session.refresh(dashboard)

    assert dashboard.id is not None
    assert dashboard.user_id == user.id
    assert dashboard.name == "My Dashboard"
    assert dashboard.description == "A test dashboard"
    # 默认值验证
    assert dashboard.is_published is False
    assert dashboard.share_token is None


@pytest.mark.asyncio
async def test_create_chart(db_session):
    """创建图表，验证 dashboard_id 关联、position/width/height。"""
    user = User(
        username="chart_owner",
        email="chart_owner@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()

    dashboard = Dashboard(user_id=user.id, name="Charts Dashboard")
    db_session.add(dashboard)
    await db_session.commit()
    await db_session.refresh(dashboard)

    chart = Chart(
        dashboard_id=dashboard.id,
        chart_type="bar",
        title="Sales Chart",
        position_x=10.0,
        position_y=20.0,
        width=500.0,
        height=400.0,
    )
    db_session.add(chart)
    await db_session.commit()
    await db_session.refresh(chart)

    assert chart.id is not None
    assert chart.dashboard_id == dashboard.id
    assert chart.chart_type == "bar"
    assert chart.title == "Sales Chart"
    assert chart.position_x == 10.0
    assert chart.position_y == 20.0
    assert chart.width == 500.0
    assert chart.height == 400.0
    # 默认值验证
    assert chart.config_json == "{}"
    assert chart.sort_order == 0


@pytest.mark.asyncio
async def test_create_datasource(db_session):
    """创建数据源，验证 source_type 和 raw_data 存储。"""
    user = User(
        username="ds_owner",
        email="ds_owner@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    datasource = DataSource(
        user_id=user.id,
        name="API Source",
        source_type="api",
        config_json='{"url": "https://api.example.com"}',
        raw_data='[{"id": 1, "value": 100}]',
    )
    db_session.add(datasource)
    await db_session.commit()
    await db_session.refresh(datasource)

    assert datasource.id is not None
    assert datasource.user_id == user.id
    assert datasource.name == "API Source"
    assert datasource.source_type == "api"
    assert datasource.config_json == '{"url": "https://api.example.com"}'
    assert datasource.raw_data == '[{"id": 1, "value": 100}]'
