"""Validation rules for user-supplied SQL queries and data-source targets."""

from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from typing import Callable, Iterable

import sqlglot
from sqlglot import exp


class SQLPolicyError(ValueError):
    """Raised when a SQL query or connection target violates the policy."""


class SQLPolicy:
    _DIALECTS = {
        "postgres": "postgres",
        "postgresql": "postgres",
        "mysql": "mysql",
        "sqlite": "sqlite",
    }
    _WRITE_EXPRESSIONS = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Create,
        exp.Drop,
        exp.Alter,
        exp.TruncateTable,
        exp.Grant,
        exp.Revoke,
        exp.Command,
    )
    _METADATA_ADDRESS = ipaddress.ip_address("169.254.169.254")

    def __init__(
        self,
        allowed_hosts: set[str],
        sqlite_data_dir: Path,
        resolver: Callable[..., Iterable[tuple]] = socket.getaddrinfo,
    ) -> None:
        self.allowed_hosts = {str(host).strip().lower() for host in allowed_hosts if str(host).strip()}
        self.sqlite_data_dir = Path(sqlite_data_dir)
        self.resolver = resolver

    def validate_query(self, query: str, db_type: str) -> str:
        """Parse and normalize exactly one read-only SQL query."""
        if not isinstance(query, str) or not query.strip():
            raise SQLPolicyError("Query must be a single read-only SQL statement")

        dialect = self._dialect(db_type)
        try:
            expressions = sqlglot.parse(query, read=dialect)
        except (sqlglot.ParseError, ValueError, TypeError) as exc:
            raise SQLPolicyError("Query must be a single read-only SQL statement") from exc

        if len(expressions) != 1 or expressions[0] is None:
            raise SQLPolicyError("Query must be a single read-only SQL statement")
        expression = expressions[0]
        if not isinstance(expression, exp.Query):
            raise SQLPolicyError("Query must be a single read-only SQL statement")

        if any(expression.find(node_type) for node_type in self._WRITE_EXPRESSIONS):
            raise SQLPolicyError("Query must be a single read-only SQL statement")
        if expression.find(exp.Into):
            raise SQLPolicyError("Query must be a single read-only SQL statement")

        try:
            return expression.sql(dialect=dialect)
        except (ValueError, TypeError) as exc:
            raise SQLPolicyError("Query must be a single read-only SQL statement") from exc

    def validate_host(self, host: str) -> str:
        """Validate every resolved address and return the first address pinned as an IP."""
        original = str(host or "").strip()
        if not original:
            raise SQLPolicyError("Host is required")
        explicitly_allowed = original.lower() in self.allowed_hosts

        try:
            literal = ipaddress.ip_address(original)
        except ValueError:
            try:
                records = self.resolver(original, 0, socket.SOCK_STREAM)
            except (OSError, socket.gaierror) as exc:
                raise SQLPolicyError("Host could not be resolved") from exc
            addresses = [self._address_from_record(record) for record in records]
            if not addresses:
                raise SQLPolicyError("Host could not be resolved")
        else:
            addresses = [literal]

        addresses = [
            getattr(address, "ipv4_mapped", None) or address
            for address in addresses
        ]
        for address in addresses:
            self._validate_address(address, explicitly_allowed)
        return str(addresses[0])

    def validate_connection(self, config: dict) -> dict:
        """Return connection data with canonical SQLite paths or a pinned network IP.

        Network consumers must connect to ``host`` and may use ``original_host``
        only for driver-specific TLS/SNI and certificate hostname verification.
        """
        if not isinstance(config, dict):
            raise SQLPolicyError("Connection configuration is invalid")
        db_type = str(config.get("db_type") or "").strip().lower()
        normalized = dict(config)
        normalized["db_type"] = db_type
        if db_type == "sqlite":
            database = str(config.get("database") or ":memory:")
            if database == ":memory:":
                normalized["database"] = database
                return normalized
            data_dir = self.sqlite_data_dir.resolve()
            candidate = (data_dir / database).resolve()
            if not candidate.is_relative_to(data_dir):
                raise SQLPolicyError("SQLite database path is not allowed")
            normalized["database"] = str(candidate)
            return normalized
        if db_type not in {"postgres", "postgresql", "mysql"}:
            raise SQLPolicyError("Unsupported database type")
        original_host = str(config.get("host") or "").strip()
        normalized["host"] = self.validate_host(original_host)
        normalized["original_host"] = original_host
        return normalized

    def _dialect(self, db_type: str) -> str:
        key = str(db_type or "").strip().lower()
        try:
            return self._DIALECTS[key]
        except KeyError as exc:
            raise SQLPolicyError("Unsupported database type") from exc

    @staticmethod
    def _address_from_record(record: tuple) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        try:
            sockaddr = record[4]
            return ipaddress.ip_address(sockaddr[0])
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise SQLPolicyError("Host resolution returned an invalid address") from exc

    def _validate_address(self, address, explicitly_allowed: bool) -> None:
        if (
            address == self._METADATA_ADDRESS
            or address.is_unspecified
            or address.is_multicast
            or address.is_link_local
        ):
            raise SQLPolicyError("Host address is not allowed")
        if (address.is_private or address.is_loopback) and not explicitly_allowed:
            raise SQLPolicyError("Host address is not allowed")
