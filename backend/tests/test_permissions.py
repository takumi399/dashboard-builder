"""测试 RBAC 权限系统：角色检查、成员管理、访问控制。"""

import pytest


# ── 辅助：注册用户并返回 user info + auth headers ──
async def register_user(client, username: str, email: str, password: str = "testpass123"):
    resp = await client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    assert resp.status_code == 201, f"注册失败 {username}: {resp.text}"
    data = resp.json()
    return {
        "user_id": data["user"]["id"],
        "username": data["user"]["username"],
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }


# ── 辅助：创建看板并返回 dashboard_id ──
async def create_dashboard(client, headers: dict, name: str = "Test Dashboard"):
    resp = await client.post("/api/dashboards", json={"name": name}, headers=headers)
    assert resp.status_code == 201, f"创建看板失败: {resp.text}"
    return resp.json()["id"]


# ── 辅助：添加成员 ──
async def add_member(client, owner_headers: dict, dashboard_id: int, user_id: int, role: str):
    resp = await client.post(
        f"/api/dashboards/{dashboard_id}/members",
        json={"user_id": user_id, "role": role},
        headers=owner_headers,
    )
    assert resp.status_code == 201, f"添加成员失败: {resp.text}"


# ═══════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════


@pytest.mark.asyncio
async def test_owner_can_edit_dashboard(async_client, auth_headers):
    """owner 可以编辑自己的看板。"""
    dashboard_id = await create_dashboard(async_client, auth_headers, "Owner's Dashboard")
    resp = await async_client.put(
        f"/api/dashboards/{dashboard_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_viewer_cannot_edit(async_client, auth_headers):
    """viewer 不能编辑看板。"""
    # 创建 owner 和 viewer
    owner = await register_user(async_client, "owner1", "owner1@test.com")
    viewer = await register_user(async_client, "viewer1", "viewer1@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])
    await add_member(async_client, owner["headers"], dashboard_id, viewer["user_id"], "viewer")

    resp = await async_client.put(
        f"/api/dashboards/{dashboard_id}",
        json={"name": "Hacked"},
        headers=viewer["headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_editor_can_add_chart(async_client, auth_headers):
    """editor 可以添加图表。"""
    owner = await register_user(async_client, "owner2", "owner2@test.com")
    editor = await register_user(async_client, "editor1", "editor1@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])
    await add_member(async_client, owner["headers"], dashboard_id, editor["user_id"], "editor")

    resp = await async_client.post(
        f"/api/dashboards/{dashboard_id}/charts",
        json={"chart_type": "bar", "title": "Editor's Chart"},
        headers=editor["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Editor's Chart"


@pytest.mark.asyncio
async def test_viewer_cannot_add_chart(async_client, auth_headers):
    """viewer 不能添加图表。"""
    owner = await register_user(async_client, "owner3", "owner3@test.com")
    viewer = await register_user(async_client, "viewer2", "viewer2@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])
    await add_member(async_client, owner["headers"], dashboard_id, viewer["user_id"], "viewer")

    resp = await async_client.post(
        f"/api/dashboards/{dashboard_id}/charts",
        json={"chart_type": "bar", "title": "Viewer's Chart"},
        headers=viewer["headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_member(async_client, auth_headers):
    """owner 可以添加成员。"""
    owner = await register_user(async_client, "owner4", "owner4@test.com")
    editor = await register_user(async_client, "editor2", "editor2@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])

    resp = await async_client.post(
        f"/api/dashboards/{dashboard_id}/members",
        json={"user_id": editor["user_id"], "role": "editor"},
        headers=owner["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["user_id"] == editor["user_id"]
    assert resp.json()["role"] == "editor"
    assert resp.json()["username"] == "editor2"


@pytest.mark.asyncio
async def test_remove_member(async_client, auth_headers):
    """owner 可以移除成员。"""
    owner = await register_user(async_client, "owner5", "owner5@test.com")
    editor = await register_user(async_client, "editor3", "editor3@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])
    await add_member(async_client, owner["headers"], dashboard_id, editor["user_id"], "editor")

    resp = await async_client.delete(
        f"/api/dashboards/{dashboard_id}/members/{editor['user_id']}",
        headers=owner["headers"],
    )
    assert resp.status_code == 204

    # 验证已移除：该用户后续无权访问
    resp = await async_client.get(
        f"/api/dashboards/{dashboard_id}",
        headers=editor["headers"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_non_member_access_denied(async_client, auth_headers):
    """非成员不能访问看板。"""
    owner = await register_user(async_client, "owner6", "owner6@test.com")
    stranger = await register_user(async_client, "stranger", "stranger@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])

    resp = await async_client.get(
        f"/api/dashboards/{dashboard_id}",
        headers=stranger["headers"],
    )
    assert resp.status_code == 404  # 不暴露看板存在


@pytest.mark.asyncio
async def test_owner_sees_all_dashboards(async_client, auth_headers):
    """owner 的看板列表包含自己的 + 被邀请的看板，并且标注了角色。"""
    owner = await register_user(async_client, "owner7", "owner7@test.com")
    other_owner = await register_user(async_client, "other_owner", "other_owner@test.com")
    dashboard_id = await create_dashboard(async_client, other_owner["headers"], "Shared Dashboard")
    await add_member(async_client, other_owner["headers"], dashboard_id, owner["user_id"], "editor")

    resp = await async_client.get("/api/dashboards", headers=owner["headers"])
    assert resp.status_code == 200
    dashboards = resp.json()
    # 应该至少看到共享的看板
    assert len(dashboards) >= 1
    # 找到被共享的看板
    shared = next((d for d in dashboards if d["id"] == dashboard_id), None)
    assert shared is not None
    assert shared["role"] == "editor"


@pytest.mark.asyncio
async def test_non_owner_cannot_add_member(async_client, auth_headers):
    """非 owner（如 editor）不能添加成员。"""
    owner = await register_user(async_client, "owner8", "owner8@test.com")
    editor = await register_user(async_client, "editor4", "editor4@test.com")
    another = await register_user(async_client, "another", "another@test.com")
    dashboard_id = await create_dashboard(async_client, owner["headers"])
    await add_member(async_client, owner["headers"], dashboard_id, editor["user_id"], "editor")

    resp = await async_client.post(
        f"/api/dashboards/{dashboard_id}/members",
        json={"user_id": another["user_id"], "role": "viewer"},
        headers=editor["headers"],
    )
    assert resp.status_code == 403
