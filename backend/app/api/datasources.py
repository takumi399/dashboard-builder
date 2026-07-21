import json, csv, io, re, asyncio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text as sa_text
from app.core.database import get_db
from app.core.config import settings
from app.core.limiter import limiter
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import DataSource
from app.schemas.datasource import (
    DataSourceCreate, DataSourceResponse,
    PublicSQLConnectionConfig, SQLExecuteRequest, SQLExecuteResponse,
)
from app.services.credential_cipher import CredentialCipher

router = APIRouter()


def _get_cipher() -> CredentialCipher:
    try:
        return CredentialCipher(settings.DATASOURCE_ENCRYPTION_KEY)
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

# ── DDL / DML 黑名单关键字（只允许 SELECT） ──
FORBIDDEN_SQL_KEYWORDS = re.compile(
    r'\b(DROP|ALTER|TRUNCATE|DELETE|UPDATE|INSERT|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b',
    re.IGNORECASE,
)
MULTI_STATEMENT = re.compile(r';\s*\S')  # 禁止多语句


def _validate_select_only(query: str) -> None:
    """校验 SQL 查询只包含 SELECT 语句，拒绝 DDL/DML。"""
    stripped = query.strip()
    if not stripped.upper().startswith('SELECT'):
        raise HTTPException(status_code=400, detail="只允许执行 SELECT 查询")
    if FORBIDDEN_SQL_KEYWORDS.search(stripped):
        raise HTTPException(status_code=400, detail="查询包含被禁止的关键字（DROP/ALTER/TRUNCATE/DELETE/UPDATE/INSERT/CREATE/GRANT/REVOKE/EXEC）")
    if MULTI_STATEMENT.search(stripped):
        raise HTTPException(status_code=400, detail="不允许执行多条 SQL 语句")


def _build_connection_url(config: dict) -> str:
    """根据 connection_config 构建 SQLAlchemy 连接 URL。"""
    db_type = config.get("db_type", "").lower()
    if db_type == "sqlite":
        database = config.get("database", ":memory:")
        return f"sqlite:///{database}"
    elif db_type == "mysql":
        user = config.get("username", "")
        pwd = config.get("password", "")
        host = config.get("host", "localhost")
        port = config.get("port", 3306)
        database = config.get("database", "")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}"
    elif db_type == "postgresql":
        user = config.get("username", "")
        pwd = config.get("password", "")
        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "")
        return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{database}"
    else:
        raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {db_type}")


def _execute_sql_sync(connection_url: str, query: str) -> dict:
    """同步执行 SQL 查询，返回 {columns, rows, row_count}。"""
    from sqlalchemy import create_engine
    engine = create_engine(connection_url)
    try:
        with engine.connect() as conn:
            result = conn.execute(sa_text(query))
            if result.returns_rows:
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                # 将不可 JSON 序列化的类型转为字符串
                for row in rows:
                    for k, v in row.items():
                        if not isinstance(v, (int, float, str, bool, type(None))):
                            row[k] = str(v)
                return {"columns": columns, "rows": rows, "row_count": len(rows)}
            else:
                return {"columns": [], "rows": [], "row_count": 0}
    finally:
        engine.dispose()


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
async def execute_sql(
    body: SQLExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对已配置的 SQL 数据源执行 SELECT 查询。"""
    # 1. 校验 SQL 语句
    _validate_select_only(body.query)

    # 2. 获取数据源
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

    # 3. 解析连接配置并构建 URL
    try:
        config = _get_cipher().decrypt(ds.connection_config)
    except ValueError:
        raise HTTPException(status_code=400, detail="连接配置格式无效")
    connection_url = _build_connection_url(config)

    # 4. 在 executor 中执行同步 SQL
    try:
        exec_result = await asyncio.get_event_loop().run_in_executor(
            None, _execute_sql_sync, connection_url, body.query,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL 执行失败: {str(e)}")

    return SQLExecuteResponse(**exec_result)


@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(datasource_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == datasource_id, DataSource.user_id == current_user.id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    await db.delete(ds)
    await db.commit()
