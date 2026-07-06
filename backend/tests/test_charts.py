"""测试图表 API：添加、列表、更新位置、删除。"""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def dashboard_id(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.post("/api/dashboards", json={"name": "图表测试看板"}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_add_chart(async_client: AsyncClient, auth_headers: dict, dashboard_id: int):
    resp = await async_client.post(f"/api/dashboards/{dashboard_id}/charts", json={
        "chart_type": "bar", "title": "销售柱状图", "position_x": 0, "position_y": 0, "width": 600, "height": 400
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["chart_type"] == "bar"
    assert data["title"] == "销售柱状图"


@pytest.mark.asyncio
async def test_list_charts(async_client: AsyncClient, auth_headers: dict, dashboard_id: int):
    # 先加一个图表
    await async_client.post(f"/api/dashboards/{dashboard_id}/charts", json={
        "chart_type": "line", "title": "趋势", "position_x": 0, "position_y": 0, "width": 400, "height": 300
    }, headers=auth_headers)
    resp = await async_client.get(f"/api/dashboards/{dashboard_id}/charts", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_chart(async_client: AsyncClient, auth_headers: dict, dashboard_id: int):
    create_resp = await async_client.post(f"/api/dashboards/{dashboard_id}/charts", json={
        "chart_type": "pie", "title": "占比", "position_x": 0, "position_y": 0, "width": 300, "height": 300
    }, headers=auth_headers)
    chart_id = create_resp.json()["id"]
    resp = await async_client.put(f"/api/dashboards/charts/{chart_id}", json={
        "position_x": 100, "position_y": 200
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["position_x"] == 100


@pytest.mark.asyncio
async def test_delete_chart(async_client: AsyncClient, auth_headers: dict, dashboard_id: int):
    create_resp = await async_client.post(f"/api/dashboards/{dashboard_id}/charts", json={
        "chart_type": "bar", "title": "待删", "position_x": 0, "position_y": 0, "width": 200, "height": 200
    }, headers=auth_headers)
    chart_id = create_resp.json()["id"]
    resp = await async_client.delete(f"/api/dashboards/charts/{chart_id}", headers=auth_headers)
    assert resp.status_code == 204
