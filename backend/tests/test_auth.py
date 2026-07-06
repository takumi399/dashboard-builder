"""测试认证 API：注册、登录、获取当前用户。"""

import pytest


@pytest.mark.asyncio
async def test_register_user(async_client):
    """POST /api/auth/register 返回 201 + access_token + user。"""
    response = await async_client.post("/api/auth/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepass123",
    })
    assert response.status_code == 201, f"注册失败: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "newuser"
    assert data["user"]["email"] == "newuser@example.com"
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client):
    """重复邮箱注册返回 400。"""
    payload = {
        "username": "dupuser",
        "email": "dup@example.com",
        "password": "pass123456",
    }
    # 第一次注册
    r1 = await async_client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201

    # 第二次注册相同邮箱
    r2 = await async_client.post("/api/auth/register", json={
        "username": "dupuser2",
        "email": "dup@example.com",
        "password": "pass123456",
    })
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(async_client):
    """POST /api/auth/login 返回 200 + access_token。"""
    # 先注册
    await async_client.post("/api/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "mypassword",
    })

    # 登录
    response = await async_client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert response.status_code == 200, f"登录失败: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "loginuser"


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    """错误密码返回 401。"""
    await async_client.post("/api/auth/register", json={
        "username": "wrongpw",
        "email": "wrongpw@example.com",
        "password": "correctpass",
    })

    response = await async_client.post("/api/auth/login", json={
        "email": "wrongpw@example.com",
        "password": "wrongpass",
    })
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user(auth_headers, async_client):
    """GET /api/auth/me 用 auth_headers 返回用户信息。"""
    response = await async_client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200, f"获取用户失败: {response.text}"
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_current_user_no_token(async_client):
    """无 token 返回 401（fastapi HTTPBearer 返回 403 或 401）。"""
    response = await async_client.get("/api/auth/me")
    assert response.status_code in (401, 403), f"期望 401/403，实际 {response.status_code}"
