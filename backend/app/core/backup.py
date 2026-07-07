"""
数据库备份工具 —— 支持 pg_dump（PostgreSQL）和 SQLite 文件复制。
"""

import os
import shutil
import subprocess
import structlog
from datetime import datetime
from pathlib import Path

from app.core.config import settings

logger = structlog.get_logger(__name__)

# 备份目录（项目根目录下的 backups/）
BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "backups"


def _ensure_backup_dir() -> Path:
    """确保备份目录存在。"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def database_url_to_pg_params(url: str) -> dict:
    """从 PostgreSQL 连接 URL 解析连接参数。"""
    # 格式: postgresql+asyncpg://user:password@host:port/dbname
    # 或者: postgresql://user:password@host:port/dbname
    url = url.replace("+asyncpg", "")
    if url.startswith("postgresql://"):
        url = url[len("postgresql://"):]
    elif url.startswith("postgres://"):
        url = url[len("postgres://"):]

    # 分离认证和主机
    if "@" in url:
        auth, host_part = url.split("@", 1)
    else:
        auth, host_part = "", url

    user = ""
    password = ""
    if ":" in auth:
        user, password = auth.split(":", 1)
    else:
        user = auth

    host = "localhost"
    port = "5432"
    dbname = ""
    if "/" in host_part:
        host_port, dbname = host_part.split("/", 1)
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host = host_port

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": dbname,
    }


def backup_database() -> str:
    """
    执行数据库备份。

    - PostgreSQL: 使用 pg_dump 导出 SQL
    - SQLite: 直接复制 .db 文件

    返回备份文件路径。
    """
    _ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_url = settings.DATABASE_URL

    if "postgresql" in db_url or "postgres" in db_url:
        params = database_url_to_pg_params(db_url)
        backup_path = BACKUP_DIR / f"backup_{timestamp}.sql"

        env = os.environ.copy()
        if params["password"]:
            env["PGPASSWORD"] = params["password"]

        cmd = [
            "pg_dump",
            "-h", params["host"],
            "-p", params["port"],
            "-U", params["user"],
            "-d", params["dbname"],
            "-f", str(backup_path),
        ]

        logger.info("开始 PostgreSQL 备份", backup_path=str(backup_path), database=params["dbname"])
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("pg_dump 失败", stderr=result.stderr)
            raise RuntimeError(f"pg_dump 失败: {result.stderr}")

        logger.info("备份完成", backup_path=str(backup_path))
        return str(backup_path)

    else:
        # SQLite: 直接复制文件
        # DATABASE_URL 格式: sqlite+aiosqlite:///./dashboard.db
        db_path = db_url.replace("sqlite+aiosqlite:///", "")
        if db_path.startswith("./"):
            db_path = str(Path(__file__).resolve().parent.parent.parent / db_path[2:])

        backup_path = BACKUP_DIR / f"backup_{timestamp}.db"
        logger.info("开始 SQLite 备份", backup_path=str(backup_path), source=db_path)

        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            logger.info("备份完成", backup_path=str(backup_path))
        else:
            logger.warning("数据库文件不存在", db_path=db_path)

        return str(backup_path)


def list_backups() -> list[dict]:
    """列出所有备份文件，按时间倒序。"""
    _ensure_backup_dir()
    backups = []
    for f in sorted(BACKUP_DIR.glob("backup_*"), reverse=True):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        })
    return backups
