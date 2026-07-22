# Dashboard Builder Development Guide

## Architecture

- Frontend: React 19, TypeScript 6, Vite 8, Ant Design 6, ECharts 6, and Zustand.
- Backend: Python 3.11, FastAPI 0.115, SQLAlchemy 2.0 async APIs, and Pydantic 2.
- Storage: SQLite in local development and PostgreSQL in the production Compose stack.
- Collaboration: authenticated WebSocket rooms per dashboard.

## Commands

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -v
uvicorn app.main:app --reload
```

```bash
cd frontend
npm ci
npm run lint
npm run build
npm run dev
```

## Code Standards

- Keep database operations asynchronous at the API persistence layer.
- Keep frontend HTTP calls in `frontend/src/services` and use explicit TypeScript types.
- Validate request and response contracts with Pydantic schemas.
- Never return or log SQL passwords, decrypted connection settings, connection URLs, or raw driver errors.
- Run SQL queries only through the policy and bounded executor services.
- Use conventional commit messages.

## SQL Security

Production Compose requires `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY`, and `DATASOURCE_ENCRYPTION_KEY`; none may be committed as a production default. SQL connections are governed by `SQL_ALLOWED_HOSTS`, `SQL_QUERY_TIMEOUT_SECONDS`, `SQL_MAX_ROWS`, and `SQLITE_DATA_DIR`. Application checks supplement, rather than replace, a read-only database account.
