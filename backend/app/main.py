import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from .core.config import settings
from .core.database import init_db
from .core.limiter import limiter
from .core.logging import setup_logging
from .api import auth, dashboards, datasources, public, ws, monitor

# 初始化结构化日志
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("服务启动", app_name=settings.APP_NAME)
    await init_db()
    yield
    logger.info("服务关闭", app_name=settings.APP_NAME)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 结构化请求日志中间件
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        "请求完成",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response

# 路由
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboards.router, prefix="/api/dashboards", tags=["dashboards"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["datasources"])
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(ws.router, tags=["ws"])
app.include_router(monitor.router, tags=["monitor"])

# 限流（可选，测试环境通过 ENV 关闭）
if settings.ENABLE_RATE_LIMIT:
    app.state.limiter = limiter
    app.add_exception_handler(429, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
