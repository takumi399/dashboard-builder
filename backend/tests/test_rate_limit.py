"""限流测试 —— 验证注册端点的 5/minute 限制。"""

import pytest


@pytest.mark.asyncio
async def test_register_rate_limit(async_client):
    """连续注册 6 次，第 6 次应返回 429 Too Many Requests。"""
    status_codes = []

    for i in range(6):
        response = await async_client.post("/api/auth/register", json={
            "username": f"ratetest{i}",
            "email": f"ratetest{i}@example.com",
            "password": "testpass123",
        })
        status_codes.append(response.status_code)

    # 前 5 次应成功（201）或返回业务错误（400 用户已存在等），但不应该是 429
    for code in status_codes[:5]:
        assert code != 429, f"前 5 次请求不应被限流，但收到 {code}"

    # 第 6 次应被限流 (429)
    assert status_codes[5] == 429, f"第 6 次请求应返回 429，但收到 {status_codes[5]}"
