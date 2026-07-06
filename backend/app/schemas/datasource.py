from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class DataSourceCreate(BaseModel):
    name: str
    source_type: str  # "csv" | "sql"
    raw_data: Optional[str] = None
    config_json: str = "{}"
    connection_config: Optional[str] = None  # JSON string for SQL connections


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    config_json: str
    raw_data: Optional[str]
    connection_config: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── SQL 数据源 schemas ──

class SQLConnectionConfig(BaseModel):
    db_type: str  # "mysql" | "postgresql" | "sqlite"
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class DataSourceSQLCreate(BaseModel):
    name: str
    source_type: Literal["sql"] = "sql"
    connection_config: SQLConnectionConfig


class SQLExecuteRequest(BaseModel):
    datasource_id: int
    query: str


class SQLExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int
