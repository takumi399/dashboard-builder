import decimal
import importlib.util
import asyncio
import socket
import sqlite3
import threading
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.services import sql_executor
from app.services.sql_executor import SQLExecutor
from app.services.sql_policy import SQLPolicy


def test_sql_executor_service_exists():
    assert importlib.util.find_spec("app.services.sql_executor") is not None


def test_bounded_worker_pool_exists():
    assert getattr(sql_executor, "BoundedWorkerPool", None) is not None


@pytest.mark.asyncio
async def test_bounded_worker_pool_holds_capacity_until_timed_out_worker_exits():
    pool = sql_executor.BoundedWorkerPool(max_workers=1, thread_name_prefix="test-sql")
    worker_started = threading.Event()
    release_worker = threading.Event()
    calls = []

    def blocked_work():
        calls.append("blocked")
        worker_started.set()
        release_worker.wait(timeout=1)
        return "late"

    try:
        with pytest.raises(asyncio.TimeoutError):
            await pool.run(blocked_work, timeout=0.01)
        assert worker_started.is_set()
        with pytest.raises(sql_executor.WorkerPoolBusy):
            await pool.run(lambda: calls.append("overflow"), timeout=0.1)
        assert calls == ["blocked"]

        release_worker.set()
        for _ in range(50):
            try:
                result = await pool.run(lambda: "recovered", timeout=0.1)
                break
            except sql_executor.WorkerPoolBusy:
                await asyncio.sleep(0.01)
        else:
            pytest.fail("worker capacity was not released after worker exit")

        assert result == "recovered"
    finally:
        release_worker.set()
        pool.shutdown()


def _create_sqlite_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        connection.executemany(
            "INSERT INTO items (name) VALUES (?)",
            [("one",), ("two",), ("three",), ("four",), ("five",)],
        )


def test_execute_limits_sqlite_rows_and_marks_truncation(tmp_path, monkeypatch):
    database = tmp_path / "items.db"
    _create_sqlite_database(database)
    monkeypatch.setattr(settings, "SQL_MAX_ROWS", 3)

    result = SQLExecutor().execute(
        {"db_type": "sqlite", "database": str(database)},
        "SELECT id, name FROM items ORDER BY id",
    )

    assert result == {
        "columns": ["id", "name"],
        "rows": [
            {"id": 1, "name": "one"},
            {"id": 2, "name": "two"},
            {"id": 3, "name": "three"},
        ],
        "row_count": 3,
        "truncated": True,
    }


def test_execute_stringifies_non_finite_sqlite_float():
    result = SQLExecutor().execute(
        {"db_type": "sqlite", "database": ":memory:"},
        "SELECT 1e999 AS value",
    )

    assert result["rows"] == [{"value": "inf"}]


def test_execute_uses_normalized_sqlite_path_instead_of_process_cwd(
    tmp_path, monkeypatch
):
    data_dir = tmp_path / "allowed-data"
    data_dir.mkdir()
    database = data_dir / "items.db"
    _create_sqlite_database(database)
    process_dir = tmp_path / "process-cwd"
    process_dir.mkdir()
    monkeypatch.chdir(process_dir)

    policy = SQLPolicy(set(), data_dir)
    normalized = policy.validate_connection(
        {"db_type": "sqlite", "database": "items.db"}
    )
    result = SQLExecutor().execute(normalized, "SELECT count(*) AS count FROM items")

    assert normalized["database"] == str(database.resolve())
    assert result["rows"] == [{"count": 5}]


def test_execute_does_not_create_missing_sqlite_target(tmp_path):
    missing_database = tmp_path / "missing.db"

    with pytest.raises(OperationalError):
        SQLExecutor().execute(
            {"db_type": "sqlite", "database": str(missing_database)},
            "SELECT 1 AS value",
        )

    assert not missing_database.exists()


class _FakeResult:
    returns_rows = True

    def __init__(self, rows=None):
        self._rows = rows or [(decimal.Decimal("1.25"),)]
        self.fetch_sizes = []

    def keys(self):
        return ["value"]

    def fetchmany(self, size):
        self.fetch_sizes.append(size)
        return self._rows


class _FakeConnection:
    def __init__(self, result):
        self.result = result
        self.executed = []
        self.driver_sql = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query):
        self.executed.append(str(query))
        return self.result

    def exec_driver_sql(self, query):
        self.driver_sql.append(query)


class _FakeEngine:
    def __init__(self, result=None, error=None):
        self.connection = _FakeConnection(result or _FakeResult())
        self.error = error
        self.disposed = False

    def connect(self):
        if self.error:
            raise self.error
        return self.connection

    def dispose(self):
        self.disposed = True


def test_network_execution_uses_pinned_ip_and_url_encodes_credentials(
    tmp_path, monkeypatch
):
    calls = []
    resolver_calls = []
    engine = _FakeEngine()

    def fake_create_engine(url, **kwargs):
        calls.append((url, kwargs))
        return engine

    monkeypatch.setattr(sql_executor, "create_engine", fake_create_engine, raising=False)
    monkeypatch.setattr(settings, "SQL_MAX_ROWS", 3)
    monkeypatch.setattr(settings, "SQL_QUERY_TIMEOUT_SECONDS", 7)
    policy = SQLPolicy(
        {"database.example"},
        tmp_path,
        resolver=lambda host, *_args, **_kwargs: resolver_calls.append(host) or [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("203.0.113.9", 5432),
            )
        ],
    )
    normalized = policy.validate_connection(
        {
            "db_type": "postgresql",
            "host": "database.example",
            "port": 5432,
            "database": "analytics",
            "username": "reader@tenant",
            "password": "p@ss:/?# word",
        }
    )

    result = SQLExecutor().execute(
        normalized,
        "SELECT amount AS value FROM invoices",
    )

    url, kwargs = calls[0]
    assert resolver_calls == ["database.example"]
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "203.0.113.9"
    assert url.username == "reader@tenant"
    assert url.password == "p@ss:/?# word"
    assert "reader%40tenant" in url.render_as_string(hide_password=False)
    assert "p%40ss%3A%2F%3F%23 word" in url.render_as_string(hide_password=False)
    assert "database.example" not in url.render_as_string(hide_password=False)
    assert kwargs["connect_args"]["options"] == (
        "-c default_transaction_read_only=on -c statement_timeout=7000"
    )
    assert engine.connection.result.fetch_sizes == [4]
    assert result["rows"] == [{"value": "1.25"}]
    assert engine.disposed is True


def test_postgresql_tls_uses_hostaddr_for_pinned_ip_and_original_host_for_identity(
    monkeypatch,
):
    calls = []
    engine = _FakeEngine()
    monkeypatch.setattr(
        sql_executor,
        "create_engine",
        lambda url, **kwargs: calls.append((url, kwargs)) or engine,
        raising=False,
    )

    SQLExecutor().execute(
        {
            "db_type": "postgresql",
            "host": "203.0.113.9",
            "original_host": "database.example",
            "port": 5432,
            "database": "analytics",
            "username": "reader",
            "password": "secret",
            "sslmode": "verify-full",
        },
        "SELECT 1 AS value",
    )

    url, kwargs = calls[0]
    assert url.host == "203.0.113.9"
    assert kwargs["connect_args"]["hostaddr"] == "203.0.113.9"
    assert kwargs["connect_args"]["host"] == "database.example"
    assert kwargs["connect_args"]["sslmode"] == "verify-full"


def test_postgresql_sslmode_disable_is_passed_to_driver(monkeypatch):
    calls = []
    engine = _FakeEngine()
    monkeypatch.setattr(
        sql_executor,
        "create_engine",
        lambda url, **kwargs: calls.append((url, kwargs)) or engine,
        raising=False,
    )

    SQLExecutor().execute(
        {
            "db_type": "postgresql",
            "host": "203.0.113.9",
            "original_host": "database.example",
            "database": "analytics",
            "sslmode": "disable",
        },
        "SELECT 1 AS value",
    )

    _, kwargs = calls[0]
    assert kwargs["connect_args"]["sslmode"] == "disable"


def test_mysql_engine_is_read_only_and_has_driver_timeouts(monkeypatch):
    calls = []
    engine = _FakeEngine()
    monkeypatch.setattr(
        sql_executor,
        "create_engine",
        lambda url, **kwargs: calls.append((url, kwargs)) or engine,
        raising=False,
    )
    monkeypatch.setattr(settings, "SQL_QUERY_TIMEOUT_SECONDS", 6)

    SQLExecutor().execute(
        {
            "db_type": "mysql",
            "host": "203.0.113.10",
            "original_host": "mysql.example",
            "port": 3306,
            "database": "analytics",
            "username": "reader",
            "password": "secret",
        },
        "SELECT 1 AS value",
    )

    url, kwargs = calls[0]
    assert url.drivername == "mysql+pymysql"
    assert url.host == "203.0.113.10"
    assert kwargs["connect_args"]["connect_timeout"] == 6
    assert kwargs["connect_args"]["read_timeout"] == 6
    assert kwargs["connect_args"]["write_timeout"] == 6
    assert kwargs["connect_args"]["init_command"] == "SET SESSION TRANSACTION READ ONLY"
    assert engine.connection.driver_sql == ["SET SESSION MAX_EXECUTION_TIME=6000"]


def test_mysql_tls_fails_closed_when_pinned_ip_differs_from_certificate_host(
    monkeypatch,
):
    called = False

    def fake_create_engine(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(sql_executor, "create_engine", fake_create_engine, raising=False)

    with pytest.raises(ValueError, match="MySQL TLS cannot verify a pinned target"):
        SQLExecutor().execute(
            {
                "db_type": "mysql",
                "host": "203.0.113.10",
                "original_host": "mysql.example",
                "port": 3306,
                "database": "analytics",
                "username": "reader",
                "password": "secret",
                "ssl_ca": "ca.pem",
                "ssl_verify_identity": True,
            },
            "SELECT 1 AS value",
        )

    assert called is False


def test_engine_is_disposed_when_execution_fails(monkeypatch):
    engine = _FakeEngine(error=RuntimeError("connection failed"))
    monkeypatch.setattr(
        sql_executor, "create_engine", lambda *_args, **_kwargs: engine, raising=False
    )

    with pytest.raises(RuntimeError, match="connection failed"):
        SQLExecutor().execute(
            {"db_type": "sqlite", "database": ":memory:"}, "SELECT 1"
        )

    assert engine.disposed is True
