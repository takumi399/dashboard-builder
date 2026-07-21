from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_type: Literal["csv", "sql"]
    raw_data: Optional[str] = None
    config_json: str = "{}"
    connection_config: Optional["SQLConnectionConfig"] = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    config_json: str
    created_at: datetime
    connection: Optional["PublicSQLConnectionConfig"] = None

    model_config = {"from_attributes": True}


# ── SQL 数据源 schemas ──

class SQLConnectionConfig(BaseModel):
    db_type: Literal["sqlite", "mysql", "postgresql"]
    host: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    database: str
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, repr=False)
    sslmode: Optional[
        Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
    ] = None
    sslrootcert: Optional[str] = None
    sslcert: Optional[str] = None
    sslkey: Optional[str] = Field(default=None, repr=False)
    ssl: Optional[bool | dict[str, object]] = Field(default=None, repr=False)
    ssl_ca: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = Field(default=None, repr=False)
    ssl_verify_cert: Optional[bool] = None
    ssl_verify_identity: Optional[bool] = None

    model_config = {"extra": "forbid"}


class PublicSQLConnectionConfig(BaseModel):
    db_type: Literal["sqlite", "mysql", "postgresql"]
    host: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    database: str
    username: Optional[str] = None


class SQLExecuteRequest(BaseModel):
    datasource_id: int
    query: str


class SQLExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool = False
