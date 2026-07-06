"""测试看板 CRUD API：创建、列表、详情、更新、删除、权限隔离。"""

import pytest


@pytest.mark.asyncio
async def test_create_dashboard(auth_headers, async_client):
    """POST /api/dashboards 返回 201。"""
    response = await async_client.post("/api/dashboards", json={
        "name": "My Dashboard",
        "description": "Test dashboard description",
    }, headers=auth_headers)
    assert response.status_code == 201, f"创建失败: {response.text}"
    data = response.json()
    assert data["name"] == "My Dashboard"
    assert data["description"] == "Test dashboard description"
    assert data["is_published"] is False
    assert data["id"] is not None
    assert "charts" in data


@pytest.mark.asyncio
async def test_list_dashboards(auth_headers, async_client):
    """GET /api/dashboards 返回列表。"""
    # 先创建两个看板
    for name in ["Dashboard A", "Dashboard B"]:
        await async_client.post("/api/dashboards", json={
            "name": name, "description": f"Description for {name}"
        }, headers=auth_headers)

    response = await async_client.get("/api/dashboards", headers=auth_headers)
    assert response.status_code == 200, f"列表失败: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["name"] in ("Dashboard A", "Dashboard B")
    assert "chart_count" in data[0]


@pytest.mark.asyncio
async def test_get_dashboard(auth_headers, async_client):
    """GET /api/dashboards/{id} 返回详情。"""
    # 创建
    create_resp = await async_client.post("/api/dashboards", json={
        "name": "Detail Dashboard", "description": "Get me"
    }, headers=auth_headers)
    dash_id = create_resp.json()["id"]

    # 获取
    response = await async_client.get(f"/api/dashboards/{dash_id}", headers=auth_headers)
    assert response.status_code == 200, f"获取失败: {response.text}"
    data = response.json()
    assert data["id"] == dash_id
    assert data["name"] == "Detail Dashboard"
    assert data["description"] == "Get me"


@pytest.mark.asyncio
async def test_update_dashboard(auth_headers, async_client):
    """PUT /api/dashboards/{id} 更新名称。"""
    create_resp = await async_client.post("/api/dashboards", json={
        "name": "Old Name", "description": "Old Desc"
    }, headers=auth_headers)
    dash_id = create_resp.json()["id"]

    response = await async_client.put(f"/api/dashboards/{dash_id}", json={
        "name": "New Name",
    }, headers=auth_headers)
    assert response.status_code == 200, f"更新失败: {response.text}"
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Old Desc"  # description 未传，保持原值


@pytest.mark.asyncio
async def test_delete_dashboard(auth_headers, async_client):
    """DELETE /api/dashboards/{id} 返回 204。"""
    create_resp = await async_client.post("/api/dashboards", json={
        "name": "To Delete", "description": ""
    }, headers=auth_headers)
    dash_id = create_resp.json()["id"]

    response = await async_client.delete(f"/api/dashboards/{dash_id}", headers=auth_headers)
    assert response.status_code == 204, f"删除失败: {response.text}"

    # 确认已删除
    get_resp = await async_client.get(f"/api/dashboards/{dash_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_others_dashboard(async_client):
    """用户 A 不能访问用户 B 的看板。"""
    # 注册用户 A
    r_a = await async_client.post("/api/auth/register", json={
        "username": "user_a", "email": "a@example.com", "password": "pass_a"
    })
    token_a = r_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 用户 A 创建看板
    dash_resp = await async_client.post("/api/dashboards", json={
        "name": "A's Dashboard", "description": ""
    }, headers=headers_a)
    dash_id = dash_resp.json()["id"]

    # 注册用户 B
    r_b = await async_client.post("/api/auth/register", json={
        "username": "user_b", "email": "b@example.com", "password": "pass_b"
    })
    token_b = r_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 用户 B 尝试访问用户 A 的看板 → 404
    response = await async_client.get(f"/api/dashboards/{dash_id}", headers=headers_b)
    assert response.status_code == 404, f"期望 404，实际 {response.status_code}"
