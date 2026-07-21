from pathlib import Path
import socket

import pytest

from app.services.sql_policy import SQLPolicy, SQLPolicyError


def _resolver_for(mapping):
    def resolver(host, *args, **kwargs):
        addresses = mapping[host]
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (address, 5432))
            for address in addresses
        ]

    return resolver


@pytest.fixture
def policy(tmp_path: Path):
    resolver = _resolver_for(
        {
            "public.example": ["8.8.8.8"],
            "private.example": ["10.0.0.5"],
            "mixed.example": ["10.0.0.5", "8.8.8.8"],
            "docker": ["172.18.0.2"],
            "localhost": ["127.0.0.1"],
        }
    )
    return SQLPolicy({"docker", "localhost", "127.0.0.1"}, tmp_path, resolver=resolver)


def test_validate_query_accepts_select(policy):
    normalized = policy.validate_query(" select id, name from users ", "postgresql")

    assert normalized == "SELECT id, name FROM users"


def test_validate_query_accepts_cte_select(policy):
    normalized = policy.validate_query(
        "WITH totals AS (SELECT count(*) AS n FROM sales) SELECT n FROM totals",
        "sqlite",
    )

    assert normalized.startswith("WITH totals AS (SELECT COUNT(*) AS n FROM sales) SELECT n FROM totals")


@pytest.mark.parametrize(
    "query",
    [
        "SELECT 1; SELECT 2",
        "SELECT 1; DELETE FROM users",
        "INSERT INTO users VALUES (1)",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "CREATE TABLE users (id INT)",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN x INT",
        "TRUNCATE TABLE users",
        "GRANT SELECT ON users TO guest",
        "REVOKE SELECT ON users FROM guest",
        "EXECUTE some_proc()",
        "SELECT id INTO archive FROM users",
        "VALUES (1)",
    ],
)
def test_validate_query_rejects_non_read_only_queries(policy, query):
    with pytest.raises(SQLPolicyError, match="single read-only"):
        policy.validate_query(query, "postgresql")


def test_validate_host_rejects_empty_host(policy):
    with pytest.raises(SQLPolicyError, match="Host is required"):
        policy.validate_host("  ")


@pytest.mark.parametrize("host", ["169.254.169.254", "224.0.0.1", "fe80::1"])
def test_validate_host_rejects_unsafe_addresses(policy, host):
    direct = SQLPolicy({host}, Path("."), resolver=lambda *_args, **_kwargs: [])

    with pytest.raises(SQLPolicyError, match="not allowed"):
        direct.validate_host(host)


def test_validate_host_rejects_ipv4_mapped_metadata_address(tmp_path):
    host = "::ffff:169.254.169.254"
    policy = SQLPolicy({host}, tmp_path, resolver=lambda *_args, **_kwargs: [])

    with pytest.raises(SQLPolicyError, match="not allowed"):
        policy.validate_host(host)


def test_validate_host_pins_ipv4_mapped_address_as_ipv4(tmp_path):
    host = "::ffff:8.8.8.8"
    policy = SQLPolicy({host}, tmp_path, resolver=lambda *_args, **_kwargs: [])

    assert policy.validate_host(host) == "8.8.8.8"


def test_validate_host_rejects_private_address_without_allowlist(policy):
    with pytest.raises(SQLPolicyError, match="not allowed"):
        policy.validate_host("private.example")


def test_validate_host_allows_explicit_private_and_loopback_hosts(policy):
    policy.validate_host("docker")
    policy.validate_host("localhost")
    policy.validate_host("127.0.0.1")


def test_validate_host_rejects_public_host_without_allowlist(policy):
    with pytest.raises(SQLPolicyError, match="not allowed"):
        policy.validate_host("public.example")


def test_validate_host_rejects_any_disallowed_address_from_hostname(policy):
    with pytest.raises(SQLPolicyError, match="not allowed"):
        policy.validate_host("mixed.example")


def test_validate_connection_allows_memory_sqlite(policy):
    assert policy.validate_connection(
        {"db_type": "sqlite", "database": ":memory:"}
    ) == {"db_type": "sqlite", "database": ":memory:"}


def test_validate_connection_confines_sqlite_path(policy, tmp_path):
    normalized = policy.validate_connection(
        {"db_type": "sqlite", "database": "nested/app.db", "label": "legacy"}
    )

    assert normalized == {
        "db_type": "sqlite",
        "database": str((tmp_path / "nested/app.db").resolve()),
        "label": "legacy",
    }

    with pytest.raises(SQLPolicyError, match="SQLite database path is not allowed"):
        policy.validate_connection({"db_type": "sqlite", "database": "../outside.db"})


def test_validate_connection_validates_network_host(policy):
    with pytest.raises(SQLPolicyError, match="Host is required"):
        policy.validate_connection({"db_type": "postgresql", "host": ""})

    policy.validate_connection({"db_type": "postgresql", "host": "docker"})


def test_validate_connection_pins_first_validated_dns_answer(tmp_path):
    calls = []

    def changing_resolver(host, *args, **kwargs):
        calls.append(host)
        address = "8.8.8.8" if len(calls) == 1 else "169.254.169.254"
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, 5432),
            )
        ]

    policy = SQLPolicy({"db.example"}, tmp_path, resolver=changing_resolver)

    normalized = policy.validate_connection(
        {
            "db_type": "postgresql",
            "host": "db.example",
            "port": 5432,
            "database": "dashboard",
        }
    )

    assert calls == ["db.example"]
    assert normalized == {
        "db_type": "postgresql",
        "host": "8.8.8.8",
        "original_host": "db.example",
        "port": 5432,
        "database": "dashboard",
    }
