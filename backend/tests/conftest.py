"""pytest 全局配置：测试数据库、HTTP 客户端、认证 fixture。"""

import os

TEST_DATASOURCE_ENCRYPTION_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
os.environ["DATASOURCE_ENCRYPTION_KEY"] = TEST_DATASOURCE_ENCRYPTION_KEY

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app

# 测试环境关闭限流
settings.ENABLE_RATE_LIMIT = False


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    """每个测试前清空限流器状态。"""
    from app.main import app as _app
    try:
        _app.state.limiter.reset()
    except Exception:
        pass
    yield


TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """会话级别的测试数据库引擎，使用 StaticPool 确保内存数据库共享。"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def setup_db(test_engine):
    """每个测试前创建所有表，测试后清理。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine):
    """提供数据库 session，用于模型单元测试。"""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(test_engine):
    """httpx.AsyncClient 连接到 FastAPI app，get_db 已 override 指向测试数据库。"""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(async_client):
    """注册测试用户、登录获取 JWT token，返回带 Authorization header 的 dict。"""
    response = await async_client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
    })
    assert response.status_code == 201, f"注册失败: {response.text}"
    data = response.json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}
