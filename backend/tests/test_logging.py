"""结构化日志和监控端点测试。"""

import pytest


@pytest.mark.asyncio
async def test_stats_endpoint(async_client):
    """GET /api/stats 返回 200 并包含 users/dashboards/charts。"""
    response = await async_client.get("/api/stats")
    assert response.status_code == 200, f"stats 端点应返回 200，但收到 {response.status_code}"
    data = response.json()
    assert "users" in data, f"响应应包含 'users' 字段，收到: {list(data.keys())}"
    assert "dashboards" in data, f"响应应包含 'dashboards' 字段，收到: {list(data.keys())}"
    assert "charts" in data, f"响应应包含 'charts' 字段，收到: {list(data.keys())}"
    assert isinstance(data["users"], int)
    assert isinstance(data["dashboards"], int)
    assert isinstance(data["charts"], int)


@pytest.mark.asyncio
async def test_stats_endpoint_counts(async_client, auth_headers):
    """创建看板和图表后，stats 计数应正确反映。"""
    # 初始状态
    initial = (await async_client.get("/api/stats")).json()
    initial_dashboards = initial["dashboards"]
    initial_charts = initial["charts"]

    # 创建一个看板
    resp = await async_client.post("/api/dashboards", json={
        "name": "Stats Test Dashboard",
        "description": "Test",
    }, headers=auth_headers)
    assert resp.status_code == 201

    dashboard_id = resp.json()["id"]

    # 创建一个图表
    resp = await async_client.post(f"/api/dashboards/{dashboard_id}/charts", json={
        "chart_type": "bar",
        "title": "Test Chart",
        "position_x": 0,
        "position_y": 0,
        "width": 400,
        "height": 300,
    }, headers=auth_headers)
    assert resp.status_code == 201

    # 检查计数
    updated = (await async_client.get("/api/stats")).json()
    assert updated["dashboards"] == initial_dashboards + 1
    assert updated["charts"] == initial_charts + 1
