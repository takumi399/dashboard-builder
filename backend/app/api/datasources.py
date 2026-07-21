import asyncio
import csv
import io
import json
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.config import (
    DEVELOPMENT_DATASOURCE_ENCRYPTION_KEY,
    settings,
)
from app.core.limiter import limiter
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import DataSource
from app.schemas.datasource import (
    DataSourceCreate, DataSourceResponse,
    PublicSQLConnectionConfig, SQLExecuteRequest, SQLExecuteResponse,
)
from app.services.credential_cipher import CredentialCipher, ENCRYPTED_PREFIX
from app.services.sql_executor import BoundedWorkerPool, SQLExecutor, WorkerPoolBusy
from app.services.sql_policy import SQLPolicy, SQLPolicyError

router = APIRouter()
logger = structlog.get_logger(__name__)
policy = SQLPolicy(
    {
        host.strip()
        for host in settings.SQL_ALLOWED_HOSTS.split(",")
        if host.strip()
    },
    Path(settings.SQLITE_DATA_DIR),
)
executor = SQLExecutor()
validation_pool = BoundedWorkerPool(
    max_workers=4,
    thread_name_prefix="sql-policy",
)
execution_pool = BoundedWorkerPool(
    max_workers=4,
    thread_name_prefix="sql-execute",
)


def _get_cipher() -> CredentialCipher:
    key = settings.DATASOURCE_ENCRYPTION_KEY
    if settings.DEBUG and not key:
        key = DEVELOPMENT_DATASOURCE_ENCRYPTION_KEY
    try:
        return CredentialCipher(key)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Data-source credentials are unavailable") from exc


def _to_response(ds: DataSource, cipher: CredentialCipher) -> DataSourceResponse:
    connection = None
    if ds.source_type == "sql":
        if not ds.connection_config:
            raise HTTPException(status_code=500, detail="Stored data-source credentials are invalid")
        try:
            config = cipher.decrypt(ds.connection_config)
            connection = PublicSQLConnectionConfig.model_validate(cipher.public_config(config))
        except (ValueError, TypeError):
            raise HTTPException(status_code=500, detail="Stored data-source credentials are invalid")
    return DataSourceResponse(
        id=ds.id,
        name=ds.name,
        source_type=ds.source_type,
        config_json=ds.config_json,
        created_at=ds.created_at,
        connection=connection,
    )

@router.get("", response_model=list[DataSourceResponse])
@limiter.limit("30/minute")
async def list_datasources(request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.user_id == current_user.id).order_by(DataSource.created_at.desc()))
    cipher = _get_cipher()
    return [_to_response(ds, cipher) for ds in result.scalars().all()]


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_datasource(
    request: Request,
    body: DataSourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建数据源（支持 CSV / SQL 类型）。"""
    if body.source_type not in ("csv", "sql"):
        raise HTTPException(status_code=400, detail="source_type 必须是 csv 或 sql")
    if body.source_type == "sql" and not body.connection_config:
        raise HTTPException(status_code=400, detail="SQL 数据源必须提供 connection_config")
    cipher = _get_cipher()
    encrypted_config = None
    if body.connection_config is not None:
        encrypted_config = cipher.encrypt(body.connection_config.model_dump(exclude_none=True))
    ds = DataSource(
        user_id=current_user.id,
        name=body.name,
        source_type=body.source_type,
        config_json=body.config_json,
        raw_data=body.raw_data,
        connection_config=encrypted_config,
    )
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return _to_response(ds, cipher)


@router.post("/upload", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(name: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = await file.read()
    text = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    ds = DataSource(user_id=current_user.id, name=name, source_type="csv", raw_data=json.dumps(rows), config_json=json.dumps({"filename": file.filename, "columns": list(rows[0].keys()), "row_count": len(rows)}))
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return _to_response(ds, _get_cipher())


@router.get("/{datasource_id}/data")
async def get_datasource_data(
    datasource_id: int,
    offset: int = 0,
    limit: int = 500,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DataSource).where(DataSource.id == datasource_id, DataSource.user_id == current_user.id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    rows = json.loads(ds.raw_data or "[]")
    total = len(rows)
    paginated_rows = rows[offset:offset + limit]
    return {
        "id": ds.id,
        "name": ds.name,
        "columns": json.loads(ds.config_json).get("columns", []),
        "rows": paginated_rows,
        "row_count": len(paginated_rows),
        "total": total,
    }


@router.post("/sql/execute", response_model=SQLExecuteResponse)
@limiter.limit("10/minute")
async def execute_sql(
    body: SQLExecuteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对已配置的 SQL 数据源执行 SELECT 查询。"""
    result = await db.execute(
        select(DataSource).where(
            DataSource.id == body.datasource_id,
            DataSource.user_id == current_user.id,
        )
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    if ds.source_type != "sql":
        raise HTTPException(status_code=400, detail="该数据源不是 SQL 类型")
    if not ds.connection_config:
        raise HTTPException(status_code=400, detail="数据源缺少连接配置")

    cipher = _get_cipher()
    legacy_plaintext = not ds.connection_config.startswith(ENCRYPTED_PREFIX)
    try:
        stored = cipher.decrypt(ds.connection_config)
        normalized_query = policy.validate_query(body.query, stored["db_type"])
    except SQLPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Connection configuration is invalid"
        ) from exc

    try:
        normalized_config = await validation_pool.run(
            policy.validate_connection,
            stored,
            timeout=settings.SQL_QUERY_TIMEOUT_SECONDS,
        )
    except SQLPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkerPoolBusy as exc:
        raise HTTPException(status_code=503, detail="SQL service is busy") from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="SQL connection validation timed out",
        ) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail="Connection configuration is invalid"
        ) from exc

    try:
        exec_result = await execution_pool.run(
            executor.execute,
            normalized_config,
            normalized_query,
            timeout=settings.SQL_QUERY_TIMEOUT_SECONDS + 1,
        )
    except WorkerPoolBusy as exc:
        raise HTTPException(status_code=503, detail="SQL service is busy") from exc
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="SQL query timed out") from exc
    except Exception as exc:
        logger.error(
            "database_query_failed",
            exception_class=type(exc).__name__,
            datasource_id=ds.id,
        )
        raise HTTPException(status_code=502, detail="Database query failed") from exc

    if legacy_plaintext:
        ds.connection_config = cipher.encrypt(stored)
        await db.commit()

    return SQLExecuteResponse(**exec_result)


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(datasource_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == datasource_id, DataSource.user_id == current_user.id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    await db.delete(ds)
    await db.commit()
