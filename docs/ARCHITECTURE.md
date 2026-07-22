# Dashboard Builder Architecture

## Overview

Dashboard Builder is a React single-page application backed by a FastAPI HTTP and WebSocket service. The application database uses SQLAlchemy's asynchronous APIs. SQLite is the local default, while the production Compose stack uses PostgreSQL.

```text
Browser (React)
  |-- HTTP/JSON /api --> FastAPI --> application database
  |-- WebSocket /ws --> collaboration rooms
  `-- chart data <---- CSV storage or bounded read-only SQL executor
```

## Main Flows

1. Authenticated users create dashboards and add positioned chart records.
2. CSV uploads are parsed and stored as JSON, or SQL connection configuration is encrypted before persistence.
3. Charts bind to data sources and map returned columns through `query_config`.
4. Publishing creates a share token for dashboard and chart definitions; fetching bound data still requires the authenticated data-source owner.
5. Authenticated sessions exchange chart operations over a dashboard WebSocket room. The current frontend client uses backend port `8000` directly, so production proxy routing is not yet wired for collaboration.

## SQL Data-Source Boundary

SQL access is split across focused components:

- Pydantic schemas accept driver-specific, structured connection settings.
- `CredentialCipher` encrypts persisted settings and creates redacted public representations.
- `SQLPolicy` parses a single read-only statement, confines SQLite paths, resolves network hosts once, and rejects unsafe targets.
- `SQLExecutor` uses SQLAlchemy URL objects, read-only driver settings, pinned validated addresses where supported, timeouts, and bounded fetches.
- The API converts policy failures, timeouts, and driver failures into sanitized responses.

Production Compose requires `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY`, and `DATASOURCE_ENCRYPTION_KEY` from the environment. `SQL_ALLOWED_HOSTS` is a comma-separated exception list for private or loopback destinations. `SQL_QUERY_TIMEOUT_SECONDS`, `SQL_MAX_ROWS`, and `SQLITE_DATA_DIR` bound execution. Database credentials must independently have read-only permissions.

## Persistence

- `users`: identities and password hashes.
- `dashboards`: owner, metadata, publication state, and share token.
- `dashboard_members`: role-based dashboard access.
- `charts`: visualization type, layout, data-source binding, and configuration.
- `data_sources`: CSV data or encrypted SQL connection configuration.

## Security Model

- Passwords are hashed with passlib/bcrypt and authenticated requests use JWTs.
- Dashboard and data-source routes enforce ownership or membership checks.
- Public dashboard reads require an unguessable share token.
- SQL passwords and private TLS key material never appear in API response schemas.
- SQL text is parser-validated rather than checked with string prefixes.
- Result size and execution time are bounded; low-level database errors are not exposed.
- Production secrets and SQL policy limits are environment controlled; local CORS permits `http://localhost:3000`.

## Verification

Backend tests cover authentication, authorization, collaboration, models, data sources, credential encryption, SQL policy, and SQL execution. Frontend CI runs Oxlint and a production TypeScript/Vite build independently of the backend job.
