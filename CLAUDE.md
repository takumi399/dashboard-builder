# Dashboard Builder

## Architecture
- Frontend: React 18 + TypeScript + Vite + Ant Design 5 + ECharts 5 + @dnd-kit
- Backend: Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + SQLite
- Auth: JWT (python-jose + passlib/bcrypt)

## Project Structure
frontend/ — React SPA (port 3000)
backend/  — FastAPI REST API (port 8000)

## Commands
- Backend: cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
- Frontend: cd frontend && npm run dev
- Full stack: docker-compose up

## Code Standards
- Python: type hints, async where possible
- TypeScript: strict mode, explicit types
- API: RESTful, Pydantic schemas
- Git: conventional commits

## Important
- All database ops are async
- Frontend API calls go through services/ layer
- Use Zustand for state management
