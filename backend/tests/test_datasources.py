"""测试数据源 API：CSV 上传、列表、数据查询、删除、SQL 数据源。"""

import json
import time
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.dashboard import DataSource
from app.api import datasources as datasource_api
from app.api.datasources import _get_cipher
from app.services.credential_cipher import ENCRYPTED_PREFIX
from app.core.config import settings


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
    assert data["truncated"] is False


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
    assert "read-only" in resp.json()["detail"]


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


def test_debug_empty_key_uses_development_cipher(monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "DATASOURCE_ENCRYPTION_KEY", "")
    cipher = _get_cipher()
    assert cipher.encrypt({"db_type": "sqlite", "database": ":memory:"}).startswith(ENCRYPTED_PREFIX)


def test_production_empty_key_is_rejected(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "DATASOURCE_ENCRYPTION_KEY", "")
    with pytest.raises(HTTPException) as exc_info:
        _get_cipher()
    assert exc_info.value.status_code == 500


def _successful_sql_result():
    return {
        "columns": ["value"],
        "rows": [{"value": 1}],
        "row_count": 1,
        "truncated": False,
    }


@pytest.mark.asyncio
async def test_sql_execute_times_out_without_exposing_connection_url(
    async_client: AsyncClient, auth_headers: dict, monkeypatch
):
    created = await async_client.post("/api/datasources", json={
        "name": "slow-query",
        "source_type": "sql",
        "connection_config": {"db_type": "sqlite", "database": ":memory:"},
    }, headers=auth_headers)
    datasource_id = created.json()["id"]

    class SlowExecutor:
        def execute(self, _config, _query):
            time.sleep(0.1)
            return _successful_sql_result()

    slow_executor = SlowExecutor()
    monkeypatch.setattr(datasource_api, "executor", slow_executor, raising=False)
    original_wait_for = datasource_api.asyncio.wait_for
    configured_timeouts = []

    async def fast_wait_for(awaitable, timeout):
        configured_timeouts.append(timeout)
        return await original_wait_for(awaitable, timeout=0.01)

    monkeypatch.setattr(datasource_api.asyncio, "wait_for", fast_wait_for)

    response = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": datasource_id,
        "query": "SELECT 1 AS value",
    }, headers=auth_headers)

    assert response.status_code == 504
    assert response.json() == {"detail": "SQL query timed out"}
    assert "sqlite:///" not in response.text
    assert configured_timeouts == [settings.SQL_QUERY_TIMEOUT_SECONDS + 1]


@pytest.mark.asyncio
async def test_sql_execute_uses_only_policy_normalized_config_and_query(
    async_client: AsyncClient, auth_headers: dict, monkeypatch
):
    created = await async_client.post("/api/datasources", json={
        "name": "pinned-target",
        "source_type": "sql",
        "connection_config": {
            "db_type": "postgresql",
            "host": "database.example",
            "port": 5432,
            "database": "analytics",
            "username": "reader",
            "password": "secret",
        },
    }, headers=auth_headers)
    datasource_id = created.json()["id"]
    normalized_config = {
        "db_type": "postgresql",
        "host": "203.0.113.9",
        "original_host": "database.example",
        "port": 5432,
        "database": "analytics",
        "username": "reader",
        "password": "secret",
    }
    calls = []

    class FakePolicy:
        def validate_query(self, query, db_type):
            assert query == " select 1 as value "
            assert db_type == "postgresql"
            return "SELECT 1 AS value"

        def validate_connection(self, config):
            assert config["host"] == "database.example"
            return normalized_config

    class RecordingExecutor:
        def execute(self, config, query):
            calls.append((config, query))
            return _successful_sql_result()

    monkeypatch.setattr(datasource_api, "policy", FakePolicy(), raising=False)
    monkeypatch.setattr(datasource_api, "executor", RecordingExecutor(), raising=False)

    response = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": datasource_id,
        "query": " select 1 as value ",
    }, headers=auth_headers)

    assert response.status_code == 200
    assert calls == [(normalized_config, "SELECT 1 AS value")]


@pytest.mark.asyncio
async def test_sql_execute_maps_driver_error_without_sensitive_output_or_logs(
    async_client: AsyncClient, auth_headers: dict, monkeypatch
):
    password = "driver-password"
    query = "SELECT secret_column FROM accounts"
    connection_url = f"postgresql://reader:{password}@database.example/analytics"
    created = await async_client.post("/api/datasources", json={
        "name": "driver-error",
        "source_type": "sql",
        "connection_config": {
            "db_type": "sqlite",
            "database": ":memory:",
            "password": password,
        },
    }, headers=auth_headers)
    datasource_id = created.json()["id"]
    log_calls = []

    class FailingExecutor:
        def execute(self, _config, _query):
            raise RuntimeError(connection_url)

    class RecordingLogger:
        def error(self, event, **kwargs):
            log_calls.append((event, kwargs))

    failing_executor = FailingExecutor()
    monkeypatch.setattr(datasource_api, "executor", failing_executor, raising=False)
    monkeypatch.setattr(datasource_api, "logger", RecordingLogger(), raising=False)

    response = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": datasource_id,
        "query": query,
    }, headers=auth_headers)

    assert response.status_code == 502
    assert response.json() == {"detail": "Database query failed"}
    assert password not in response.text
    assert query not in response.text
    assert connection_url not in response.text
    assert log_calls == [(
        "database_query_failed",
        {"exception_class": "RuntimeError", "datasource_id": datasource_id},
    )]


@pytest.mark.asyncio
async def test_successful_legacy_sql_execution_encrypts_stored_config(
    async_client: AsyncClient, auth_headers: dict, db_session, monkeypatch
):
    created = await async_client.post("/api/datasources", json={
        "name": "legacy-success",
        "source_type": "sql",
        "connection_config": {"db_type": "sqlite", "database": ":memory:"},
    }, headers=auth_headers)
    datasource_id = created.json()["id"]
    row = (await db_session.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )).scalar_one()
    row.connection_config = json.dumps({"db_type": "sqlite", "database": ":memory:"})
    await db_session.commit()

    class SuccessfulExecutor:
        def execute(self, _config, _query):
            return _successful_sql_result()

    monkeypatch.setattr(datasource_api, "executor", SuccessfulExecutor(), raising=False)
    response = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": datasource_id,
        "query": "SELECT 1 AS value",
    }, headers=auth_headers)

    assert response.status_code == 200
    await db_session.refresh(row)
    assert row.connection_config.startswith(ENCRYPTED_PREFIX)


@pytest.mark.asyncio
async def test_failed_legacy_sql_execution_does_not_modify_stored_config(
    async_client: AsyncClient, auth_headers: dict, db_session, monkeypatch
):
    created = await async_client.post("/api/datasources", json={
        "name": "legacy-failure",
        "source_type": "sql",
        "connection_config": {"db_type": "sqlite", "database": ":memory:"},
    }, headers=auth_headers)
    datasource_id = created.json()["id"]
    row = (await db_session.execute(
        select(DataSource).where(DataSource.id == datasource_id)
    )).scalar_one()
    plaintext = json.dumps({"db_type": "sqlite", "database": ":memory:"})
    row.connection_config = plaintext
    await db_session.commit()

    class FailingExecutor:
        def execute(self, _config, _query):
            raise RuntimeError("connection failed")

    failing_executor = FailingExecutor()
    monkeypatch.setattr(datasource_api, "executor", failing_executor, raising=False)
    response = await async_client.post("/api/datasources/sql/execute", json={
        "datasource_id": datasource_id,
        "query": "SELECT 1 AS value",
    }, headers=auth_headers)

    assert response.status_code == 502
    await db_session.refresh(row)
    assert row.connection_config == plaintext
