import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import init_db
from .api import auth, dashboards, datasources, public, ws, monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 请求日志中间件 ──
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)
    logger.info(
        "%s %s -> %d (%.2fms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboards.router, prefix="/api/dashboards", tags=["dashboards"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["datasources"])
app.include_router(public.router, prefix="/api/public", tags=["public"])
app.include_router(ws.router, tags=["ws"])
app.include_router(monitor.router, tags=["monitor"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
