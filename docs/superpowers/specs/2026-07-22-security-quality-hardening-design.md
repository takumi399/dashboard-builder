# Dashboard Builder Security And Quality Hardening Design

## Context

Dashboard Builder has meaningful backend coverage and passing GitHub Actions runs, but database connection credentials are stored and returned as part of the public data-source schema. SQL execution relies on regular-expression filtering, has no reliable execution limit, and returns raw database error text. CI validates only the backend, while README metadata, screenshots, license links, and dependency versions have drifted from the repository.

## Goals

- Encrypt persisted SQL data-source credentials and exclude secrets from API responses.
- Preserve read access to existing plaintext records while ensuring subsequent writes use encryption.
- Enforce one read-only SQL statement, approved connection targets, time limits, and bounded results.
- Add regression tests for credential handling and SQL security boundaries.
- Add frontend lint and production build validation to CI.
- Reconcile public documentation with the implemented repository state.

## Non-Goals

- No UI redesign, new chart type, or new collaboration feature.
- No live deployment or repository rename.
- No database table migration solely for credential encryption.
- No deletion of developer workflow files such as `CLAUDE.md`, prompt files, or Hermes plans.

## Credential Data Flow

Incoming connection configuration will be validated as structured data. Sensitive fields will be encrypted with `cryptography.fernet` before serialization into the existing `connection_config` column. Encryption will use an application-managed key supplied through configuration. Production startup must reject a missing or invalid key, and tests will inject an explicit fixture key instead of relying on a generated fallback.

The service layer will decrypt credentials only when opening a database connection. API response schemas will expose non-sensitive metadata such as database type, host, port, and database name, but never passwords or an encrypted payload. Existing plaintext JSON records will remain readable for compatibility and will be written back in encrypted form when they are next changed.

## SQL Execution Boundary

`sqlglot` will validate that input contains exactly one read-only query. Database connections will be restricted through an explicit allowlist configuration. Production will deny unlisted destinations, including loopback, private, link-local, and metadata-service addresses; local Docker configuration will explicitly list the development hosts it needs. Hostnames will be resolved and the resulting addresses validated before connection. Execution will use database read-only mode and driver-level statement timeouts where supported, an application timeout as a second boundary, and `fetchmany` with a configured maximum row count instead of unbounded `fetchall`.

Connection and query failures will be logged with sensitive values removed. Public responses will use stable error categories and will not echo connection URLs, passwords, SQL driver traces, or arbitrary database error messages.

## Tests

Backend regression tests will cover:

- Passwords absent from create and list responses.
- Encrypted persistence and compatibility with existing plaintext records.
- Invalid encryption configuration.
- Blocked hosts and allowed development hosts.
- DDL, DML, multiple statements, and parser edge cases.
- Query timeout behavior and result truncation.

Existing authentication, dashboard, permissions, rate-limit, logging, and WebSocket tests must continue to pass. Frontend changes will be validated by strict TypeScript compilation, Oxlint, and the Vite production build.

## CI Flow

CI will retain the backend test job and add an independent frontend job that performs a clean lockfile install, lint, and production build. Both jobs must pass for pull requests and pushes to `master`. Dependency and lockfile changes will be committed together.

## Documentation

README and `CLAUDE.md` technology versions will match package metadata. Broken placeholder badges, missing screenshot references, missing license claims, completed-feature checkboxes, and deployment instructions will be corrected. The repository will not claim screenshots, licenses, or CI checks that are absent.

## Delivery

Changes will be organized into focused conventional commits for credential and SQL hardening, tests and CI, and documentation. Before a normal fast-forward push to `master`, the complete local test/build suite, diff review, and secret scan must pass. Force-push and history rewriting are excluded.
