"""测试数据源 API：CSV 上传、列表、数据查询、删除。"""

import pytest
from httpx import AsyncClient


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
