# Dashboard Builder

[![GitHub](https://img.shields.io/badge/GitHub-dashboard--builder-181717?logo=github)](https://github.com/takumi399/dashboard-builder)

A full-stack dashboard builder for creating, arranging, publishing, and collaboratively editing data visualizations.

## Features

- Drag, resize, and configure bar, line, pie, scatter, heatmap, radar, funnel, and table visualizations.
- Upload CSV data or connect read-only SQLite, MySQL, and PostgreSQL data sources.
- Encrypt stored SQL passwords and private TLS key material, and omit them from API responses.
- Validate SQL as a single read-only statement, constrain connection targets, cap result rows, and enforce timeouts.
- Authenticate with JWT, publish dashboard definitions through share tokens, and collaborate over WebSockets in local development.
- Run with SQLite for local development or PostgreSQL through the production Compose configuration.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript 6, Vite 8, Ant Design 6, ECharts 6, Zustand |
| Backend | Python 3.11, FastAPI 0.115, SQLAlchemy 2.0, Pydantic 2 |
| Storage | SQLite for local development; PostgreSQL in production Compose |
| Quality | Pytest, Oxlint, TypeScript, GitHub Actions |

## Quick Start

Prerequisites: Python 3.11+, Node.js 22+, and optionally Docker.

```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The API runs at `http://localhost:8000` and the frontend at `http://localhost:3000`.

To run the local stack with Docker:

```bash
docker compose up --build
```

## Secure SQL Data Sources

The backend uses these environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATASOURCE_ENCRYPTION_KEY` | Fernet key used to encrypt stored SQL connection configuration | Development only; required when `DEBUG=False` |
| `POSTGRES_PASSWORD` | Password used to initialize the production PostgreSQL service | Required in production |
| `DATABASE_URL` | Async SQLAlchemy URL for the production application database | Required in production |
| `SECRET_KEY` | Secret used to sign application JWTs | Required in production |
| `SQL_ALLOWED_HOSTS` | Comma-separated hostnames allowed to resolve to private or loopback addresses | Empty |
| `SQL_QUERY_TIMEOUT_SECONDS` | Query timeout, from 1 to 60 seconds | `10` |
| `SQL_MAX_ROWS` | Maximum returned rows, from 1 to 10,000 | `1000` |
| `SQLITE_DATA_DIR` | Directory that contains allowed SQLite files | `./data` |

Generate a production encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set all required production variables before starting the production stack. `DATABASE_URL` must use the same PostgreSQL password, with reserved URL characters percent-encoded:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The application validates read-only SQL and restricts network/file targets, but the configured database account must also have read-only permissions. Do not reuse the development key in production.

Share-token views expose dashboard and chart definitions, but fetching bound data currently requires an authenticated data-source owner. The frontend WebSocket client currently connects directly to backend port `8000`; production deployments must update that client routing before enabling collaboration through the Nginx proxy.

## Quality Checks

```bash
cd backend
python -m pytest tests/ -v

cd ../frontend
npm ci
npm run lint
npm run build
```

Architecture details are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
