# Dashboard Builder — Low-Code Data Dashboard Platform

A full-stack low-code dashboard builder where users can drag-and-drop chart components onto a canvas, bind data sources, and publish interactive dashboards.

## Features

- **Drag-and-Drop Editor** — Drag bar, line, and pie charts onto a canvas. Move and resize freely.
- **Data Source Management** — Upload CSV files and bind them to charts.
- **Chart Rendering** — ECharts-powered interactive charts (bar, line, pie).
- **JWT Authentication** — Secure user registration and login with bcrypt password hashing.
- **Dashboard Publishing** — One-click publish with shareable public links.
- **Responsive UI** — Built with Ant Design 5 for a polished enterprise look.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Ant Design 5 + ECharts 5 + @dnd-kit |
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| Database | SQLite (swap to PostgreSQL via SQLAlchemy) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| State | Zustand |
| Build | Vite + TypeScript strict mode |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) Docker

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000

### Docker (Full Stack)

```bash
docker-compose up
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login |
| GET | /api/auth/me | Get current user |
| GET | /api/dashboards | List user dashboards |
| POST | /api/dashboards | Create dashboard |
| GET | /api/dashboards/:id | Get dashboard with charts |
| PUT | /api/dashboards/:id | Update dashboard |
| DELETE | /api/dashboards/:id | Delete dashboard |
| POST | /api/dashboards/:id/publish | Publish dashboard |
| GET | /api/dashboards/:id/charts | List charts |
| POST | /api/dashboards/:id/charts | Add chart |
| PUT | /api/dashboards/charts/:id | Update chart |
| DELETE | /api/dashboards/charts/:id | Delete chart |
| POST | /api/datasources/upload | Upload CSV |
| GET | /api/datasources | List data sources |
| GET | /api/datasources/:id/data | Get data source content |
| GET | /api/public/dashboards/:token | Public dashboard view |

## Project Structure

```
task/
├── frontend/              # React + TypeScript (Vite)
│   └── src/
│       ├── components/
│       │   └── charts/    # ChartRenderer — ECharts wrapper
│       ├── pages/          # Login, Register, DashboardList, Editor, View, DataSource
│       ├── services/       # API clients (axios)
│       ├── store/          # Zustand auth store
│       └── types/          # TypeScript interfaces
├── backend/               # FastAPI
│   └── app/
│       ├── api/            # Route handlers (auth, dashboards, datasources, public)
│       ├── core/           # Config, database, security
│       ├── models/         # SQLAlchemy ORM models
│       └── schemas/        # Pydantic request/response schemas
├── docker-compose.yml
└── CLAUDE.md
```

## Architecture Decision Records

- **SQLite for dev, PostgreSQL-ready**: SQLAlchemy makes swapping trivial. SQLite is zero-config for local dev.
- **Async database ops**: All endpoints use async/await for non-blocking I/O.
- **Zustand over Redux**: Minimal boilerplate. Auth state is simple — Zustand fits perfectly.
- **Model validation with Pydantic v2**: Automatic request validation and response serialization from ORM models.
- **@dnd-kit over react-beautiful-dnd**: Actively maintained, works with React 18+, supports both sortable and free-drag use cases.

## License

MIT
