"""测试数据源 API：CSV 上传、列表、数据查询、删除、SQL 数据源。"""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.dashboard import DataSource
from app.services.credential_cipher import ENCRYPTED_PREFIX


@pytest.mark.asyncio
async def test_upload_csv(async_client: AsyncClient, auth_headers: dict):
    csv_content = "name,value\nA,10\nB,20"
    files = {"file": ("data.csv", csv_content, "text/csv")}
    resp = await async_client.post("/api/datasources/upload?name=测试数据", files=files, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "测试数据"


@pytest.mark.asyncio
async def test_upload_non_csv(async_client: AsyncClient, auth_headers: dict):
    files = {"file": ("data.txt", "hello", "text/plain")}
    resp = await async_client.post("/api/datasources/upload?name=bad", files=files, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_datasources(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/datasources", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_datasource_data(async_client: AsyncClient, auth_headers: dict):
    # 先上传
    csv_content = "x,y\n1,2"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    upload_resp = await async_client.post("/api/datasources/upload?name=查询测试", files=files, headers=auth_headers)
    ds_id = upload_resp.json()["id"]
    resp = await async_client.get(f"/api/datasources/{ds_id}/data", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "columns" in data
    assert "rows" in data


@pytest.mark.asyncio
async def test_delete_datasource(async_client: AsyncClient, auth_headers: dict):
    csv_content = "a,b\n3,4"
    files = {"file": ("del.csv", csv_content, "text/csv")}
    upload_resp = await async_client.post("/api/datasources/upload?name=待删", files=files, headers=auth_headers)
    ds_id = upload_resp.json()["id"]
    resp = await async_client.delete(f"/api/datasources/{ds_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── SQL 数据源测试 ──

@pytest.mark.asyncio
async def test_create_sql_datasource(async_client: AsyncClient, auth_headers: dict):
    """创建 SQL 类型数据源（使用 SQLite :memory:）。"""
    resp = await async_client.post("/api/datasources", json={
        "name": "测试SQL数据源",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
        },
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "测试SQL数据源"
    assert data["source_type"] == "sql"
    assert data["connection"]["db_type"] == "sqlite"
    assert "raw_data" not in data


@pytest.mark.asyncio
async def test_sql_execute(async_client: AsyncClient, auth_headers: dict):
    """通过 SQL 数据源执行 SELECT 1。"""
    # 先创建 SQL 数据源
    create_resp = await async_client.post("/api/datasources", json={
        "name": "SQL执行测试",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
        },
    }, headers=auth_headers)
    ds_id = create_resp.json()["id"]

    # 执行 SELECT 1
    resp = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": ds_id,
        "query": "SELECT 1 AS value",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["columns"] == ["value"]
    assert data["rows"] == [{"value": 1}]
    assert data["row_count"] == 1


@pytest.mark.asyncio
async def test_sql_ddl_blocked(async_client: AsyncClient, auth_headers: dict):
    """执行 DROP TABLE 应该被拦截返回 400。"""
    # 先创建 SQL 数据源
    create_resp = await async_client.post("/api/datasources", json={
        "name": "DDL拦截测试",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
        },
    }, headers=auth_headers)
    ds_id = create_resp.json()["id"]

    resp = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": ds_id,
        "query": "DROP TABLE users",
    }, headers=auth_headers)
    assert resp.status_code == 400
    assert "只允许执行 SELECT" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_sql_insert_blocked(async_client: AsyncClient, auth_headers: dict):
    """执行 INSERT 应该被拦截返回 400。"""
    create_resp = await async_client.post("/api/datasources", json={
        "name": "INSERT拦截测试",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
        },
    }, headers=auth_headers)
    ds_id = create_resp.json()["id"]

    resp = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": ds_id,
        "query": "INSERT INTO t VALUES (1)",
    }, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sql_multi_statement_blocked(async_client: AsyncClient, auth_headers: dict):
    """多语句查询应该被拦截。"""
    create_resp = await async_client.post("/api/datasources", json={
        "name": "多语句拦截测试",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
        },
    }, headers=auth_headers)
    ds_id = create_resp.json()["id"]

    resp = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": ds_id,
        "query": "SELECT 1; DROP TABLE users",
    }, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sql_credentials_are_encrypted_and_redacted(
    async_client: AsyncClient, auth_headers: dict, db_session
):
    password = "top-secret"
    created = await async_client.post("/api/datasources", json={
        "name": "analytics",
        "source_type": "sql",
        "connection_config": {
            "db_type": "postgresql",
            "host": "db.example.com",
            "port": 5432,
            "database": "analytics",
            "username": "reader",
            "password": password,
        },
    }, headers=auth_headers)
    assert created.status_code == 201
    payload = created.json()
    assert password not in created.text
    assert ENCRYPTED_PREFIX not in created.text
    assert payload["connection"]["username"] == "reader"
    assert "password" not in payload["connection"]

    row = (await db_session.execute(
        select(DataSource).where(DataSource.name == "analytics")
    )).scalar_one()
    assert row.connection_config.startswith(ENCRYPTED_PREFIX)
    assert password not in row.connection_config

    listed = await async_client.get("/api/datasources", headers=auth_headers)
    assert listed.status_code == 200
    assert password not in listed.text
    assert ENCRYPTED_PREFIX not in listed.text
    assert "password" not in listed.json()[0]["connection"]


@pytest.mark.asyncio
async def test_sql_create_requires_connection_config(async_client: AsyncClient, auth_headers: dict):
    response = await async_client.post("/api/datasources", json={
        "name": "missing-config",
        "source_type": "sql",
    }, headers=auth_headers)
    assert response.status_code == 400
    assert "connection_config" in response.json()["detail"]


@pytest.mark.asyncio
async def test_legacy_plaintext_sql_credentials_are_redacted(
    async_client: AsyncClient, auth_headers: dict, db_session
):
    created = await async_client.post("/api/datasources", json={
        "name": "legacy",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
            "password": "old-secret",
        },
    }, headers=auth_headers)
    assert created.status_code == 201
    row = (await db_session.execute(
        select(DataSource).where(DataSource.name == "legacy")
    )).scalar_one()
    row.connection_config = json.dumps({
        "db_type": "sqlite",
        "database": ":memory:",
        "username": "legacy-user",
        "password": "old-secret",
    })
    await db_session.commit()

    response = await async_client.get("/api/datasources", headers=auth_headers)
    assert response.status_code == 200
    assert "old-secret" not in response.text
    legacy = next(item for item in response.json() if item["name"] == "legacy")
    assert legacy["connection"]["username"] == "legacy-user"
    assert "password" not in legacy["connection"]
