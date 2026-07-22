"""Bounded synchronous execution for validated SQL data sources."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from app.core.config import settings


class WorkerPoolBusy(RuntimeError):
    """Raised when all bounded SQL worker slots are occupied."""


class BoundedWorkerPool:
    """Run blocking SQL work without allowing an unbounded queue.

    Timing out an await cannot terminate its Python thread. The capacity slot is
    therefore released only when the underlying future actually finishes.
    """

    def __init__(self, max_workers: int, thread_name_prefix: str) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix,
        )
        self._slots = threading.BoundedSemaphore(max_workers)

    async def run(
        self,
        function: Callable[..., Any],
        *args: Any,
        timeout: float,
    ) -> Any:
        if not self._slots.acquire(blocking=False):
            raise WorkerPoolBusy("SQL worker capacity is busy")
        try:
            future = self._executor.submit(partial(function, *args))
        except BaseException:
            self._slots.release()
            raise
        future.add_done_callback(lambda _future: self._slots.release())
        wrapped = asyncio.wrap_future(future)
        try:
            return await asyncio.wait_for(asyncio.shield(wrapped), timeout=timeout)
        except asyncio.TimeoutError:
            wrapped.cancel()
            raise

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=True)


class SQLExecutor:
    """Execute policy-normalized SQL with connection and result bounds."""

    _POSTGRES_TLS_FIELDS = {"sslmode", "sslrootcert", "sslcert", "sslkey"}
    _MYSQL_TLS_FIELDS = {
        "ssl",
        "ssl_ca",
        "ssl_cert",
        "ssl_key",
        "ssl_verify_cert",
        "ssl_verify_identity",
    }

    def execute(self, config: dict, query: str) -> dict:
        timeout_seconds = settings.SQL_QUERY_TIMEOUT_SECONDS
        max_rows = settings.SQL_MAX_ROWS
        url, engine_kwargs = self._engine_config(config, timeout_seconds)
        engine = create_engine(url, **engine_kwargs)
        try:
            with engine.connect() as connection:
                cleanup = self._configure_connection(
                    connection, config, timeout_seconds
                )
                try:
                    result = connection.execute(text(query))
                    if not result.returns_rows:
                        return {
                            "columns": [],
                            "rows": [],
                            "row_count": 0,
                            "truncated": False,
                        }
                    columns = list(result.keys())
                    fetched = result.fetchmany(max_rows + 1)
                    rows = [
                        {
                            column: self._json_value(value)
                            for column, value in zip(columns, row)
                        }
                        for row in fetched[:max_rows]
                    ]
                    return {
                        "columns": columns,
                        "rows": rows,
                        "row_count": len(rows),
                        "truncated": len(fetched) > max_rows,
                    }
                finally:
                    cleanup()
        finally:
            engine.dispose()

    def _engine_config(self, config: dict, timeout_seconds: int) -> tuple[URL, dict]:
        db_type = str(config.get("db_type") or "").lower()
        self._validate_tls_options(config, db_type)
        if db_type == "sqlite":
            database = str(config.get("database") or ":memory:")
            if database != ":memory:" and not Path(database).is_absolute():
                raise ValueError("SQLite target must be a normalized absolute path")
            if database == ":memory:":
                url = URL.create("sqlite", database=database)
            else:
                url = URL.create(
                    "sqlite",
                    database=f"file:{Path(database).as_posix()}",
                    query={"mode": "ro", "uri": "true"},
                )
            return url, {
                "connect_args": {"timeout": timeout_seconds}
            }

        host = str(config.get("host") or "")
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError("Network target must be a pinned IP address") from exc

        common = {
            "username": config.get("username"),
            "password": config.get("password"),
            "host": host,
            "port": config.get("port"),
            "database": config.get("database"),
        }
        if db_type in {"postgres", "postgresql"}:
            connect_args = {
                "connect_timeout": timeout_seconds,
                "options": (
                    "-c default_transaction_read_only=on "
                    f"-c statement_timeout={timeout_seconds * 1000}"
                ),
            }
            self._configure_postgresql_tls(config, connect_args)
            return URL.create("postgresql+psycopg", **common), {
                "connect_args": connect_args
            }
        if db_type == "mysql":
            if self._mysql_tls_configured(config):
                original_host = str(config.get("original_host") or host)
                if original_host != host:
                    raise ValueError("MySQL TLS cannot verify a pinned target")
            connect_args = {
                "connect_timeout": timeout_seconds,
                "read_timeout": timeout_seconds,
                "write_timeout": timeout_seconds,
                "init_command": "SET SESSION TRANSACTION READ ONLY",
            }
            self._copy_mysql_tls_options(config, connect_args)
            return URL.create("mysql+pymysql", **common), {
                "connect_args": connect_args
            }
        raise ValueError("Unsupported database type")

    @staticmethod
    def _configure_connection(connection, config: dict, timeout_seconds: int):
        db_type = str(config.get("db_type") or "").lower()
        if db_type == "sqlite":
            connection.exec_driver_sql("PRAGMA query_only = ON")
            raw_connection = connection.connection.driver_connection
            deadline = time.monotonic() + timeout_seconds
            raw_connection.set_progress_handler(
                lambda: int(time.monotonic() >= deadline), 1000
            )
            return lambda: raw_connection.set_progress_handler(None, 0)
        if db_type == "mysql":
            connection.exec_driver_sql(
                f"SET SESSION MAX_EXECUTION_TIME={timeout_seconds * 1000}"
            )
        return lambda: None

    @staticmethod
    def _configure_postgresql_tls(config: dict, connect_args: dict) -> None:
        sslmode = config.get("sslmode")
        tls_configured = bool(
            sslmode and str(sslmode).lower() != "disable"
        ) or any(
            config.get(key)
            for key in ("sslrootcert", "sslcert", "sslkey")
        )
        if not tls_configured:
            return

        host = str(config["host"])
        original_host = str(config.get("original_host") or host)
        if original_host != host:
            connect_args["hostaddr"] = host
            connect_args["host"] = original_host
        if sslmode:
            connect_args["sslmode"] = sslmode
        for source, target in (
            ("sslrootcert", "sslrootcert"),
            ("sslcert", "sslcert"),
            ("sslkey", "sslkey"),
        ):
            if config.get(source) and target not in connect_args:
                connect_args[target] = config[source]

    @staticmethod
    def _mysql_tls_configured(config: dict) -> bool:
        return any(
            config.get(key)
            for key in (
                "ssl",
                "ssl_ca",
                "ssl_cert",
                "ssl_key",
                "ssl_verify_cert",
                "ssl_verify_identity",
            )
        )

    @staticmethod
    def _copy_mysql_tls_options(config: dict, connect_args: dict) -> None:
        for key in (
            "ssl",
            "ssl_ca",
            "ssl_cert",
            "ssl_key",
            "ssl_verify_cert",
            "ssl_verify_identity",
        ):
            if config.get(key) is not None:
                connect_args[key] = config[key]

    @classmethod
    def _validate_tls_options(cls, config: dict, db_type: str) -> None:
        configured = {
            field
            for field in cls._POSTGRES_TLS_FIELDS | cls._MYSQL_TLS_FIELDS
            if config.get(field) is not None
        }
        allowed = (
            cls._POSTGRES_TLS_FIELDS
            if db_type in {"postgres", "postgresql"}
            else cls._MYSQL_TLS_FIELDS if db_type == "mysql" else set()
        )
        unsupported = sorted(configured - allowed)
        if unsupported:
            fields = ", ".join(unsupported)
            raise ValueError(f"TLS options {fields} are not valid for {db_type}")

    @staticmethod
    def _json_value(value: Any) -> Any:
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            return str(value)
        return value
