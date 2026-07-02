# Dashboard Builder — Low-Code Data Dashboard Platform

[![GitHub](https://img.shields.io/badge/GitHub-dashboard--builder-181717?logo=github)](https://github.com/your-org/dashboard-builder)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

A full-stack low-code dashboard builder where users can drag-and-drop chart components onto a canvas, bind data sources, and publish interactive dashboards.

## Features

- [x] **Drag-and-Drop Editor** — Drag bar, line, and pie charts onto a canvas. Move and resize freely with react-rnd.
- [x] **Chart Rendering** — ECharts 5-powered interactive charts (bar, line, pie) with configurable options.
- [x] **Data Source Management** — Upload CSV files and bind them to charts with column mapping.
- [x] **JWT Authentication** — Secure user registration and login with bcrypt password hashing.
- [x] **Dashboard Publishing** — One-click publish with shareable public links (no auth required).
- [x] **Responsive UI** — Built with Ant Design 5 for a polished enterprise look.
- [x] **Vite Dev Proxy** — `/api` requests proxied to backend, avoiding CORS issues in development.
- [ ] **Multi-tenant Workspaces** — Organization-scoped dashboards and data sources.
- [ ] **Real-time Collaboration** — WebSocket-based live editing with multiple users.
- [ ] **Advanced Chart Types** — Scatter, heatmap, funnel, and custom ECharts options.
- [ ] **PostgreSQL Production** — Swap SQLite for PostgreSQL with zero code changes.

## Architecture

[View Architecture Diagram](docs/architecture.html)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite + Ant Design 5 + ECharts 5 + react-rnd |
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| Database | SQLite (swap to PostgreSQL via SQLAlchemy) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| State | Zustand |
| Build | Vite + TypeScript strict mode + Oxlint |

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

## Screenshots

<!-- TODO: Add screenshots -->
| Login | Dashboard List | Editor |
|-------|---------------|--------|
| ![login](screenshots/login.png) | ![list](screenshots/list.png) | ![editor](screenshots/editor.png) |

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
- **react-rnd for drag-and-drop**: Replaced @dnd-kit for canvas interactions. Provides native drag, resize, and absolute positioning out of the box.

## License

MIT
