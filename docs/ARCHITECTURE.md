# Architecture Document — Dashboard Builder

## Overview

Dashboard Builder is a single-page application (SPA) with a RESTful API backend. The frontend communicates with the backend exclusively via HTTP/JSON.

## System Diagram

```
┌──────────────┐       HTTP/JSON       ┌──────────────┐       SQL        ┌──────────┐
│   Browser    │ ────────────────────→  │    FastAPI   │ ──────────────→  │  SQLite  │
│  (React SPA) │ ←──────────────────── │   (Python)   │ ←────────────── │   (Dev)  │
└──────────────┘       Port 8000       └──────────────┘                  └──────────┘
     Port 3000                               │
        │                                    │ File Upload (CSV)
        │                                    ▼
        │                            ┌──────────────┐
        │                            │  Parsed JSON  │
        │                            │   in DB Text  │
        │                            └──────────────┘
        │
        ▼
┌──────────────┐
│  Vite Proxy  │  /api → localhost:8000
└──────────────┘
```

## Data Flow

### Dashboard Creation Flow
1. User creates dashboard → POST /api/dashboards → INSERT into dashboards table
2. User drags chart from palette → POST /api/dashboards/:id/charts → INSERT into charts table
3. User uploads CSV → POST /api/datasources/upload → Parse CSV → Store as JSON in raw_data
4. User binds data source to chart → PUT /api/charts/:id with data_source_id
5. Frontend fetches data via GET /api/datasources/:id/data → Renders chart with ECharts
6. User publishes → POST /api/dashboards/:id/publish → Generates share_token

### Public View Flow
1. Visitor opens /view/:token
2. Frontend calls GET /api/public/dashboards/:token (no auth required)
3. Returns dashboard + charts with positions
4. For each chart with data_source_id, fetch data via GET /api/datasources/:id/data
5. Render charts at absolute positions using ECharts

## Database Schema

```
users
├── id (PK)
├── username (UNIQUE)
├── email (UNIQUE)
├── password_hash
└── created_at

dashboards
├── id (PK)
├── user_id (FK → users)
├── name
├── description
├── is_published
├── share_token (UNIQUE)
├── created_at
└── updated_at

charts
├── id (PK)
├── dashboard_id (FK → dashboards, CASCADE)
├── chart_type (bar|line|pie)
├── title
├── position_x, position_y, width, height
├── data_source_id (FK → data_sources, SET NULL)
├── config_json (ECharts option overrides)
├── query_config (column mapping)
└── sort_order

data_sources
├── id (PK)
├── user_id (FK → users)
├── name
├── source_type (csv)
├── config_json (filename, columns, row_count)
├── raw_data (parsed CSV as JSON)
└── created_at
```

## Security

- All passwords hashed with bcrypt via passlib
- JWT tokens with configurable expiration (default 60 min)
- Token-based auth for all dashboard/data source endpoints
- Public dashboard view does NOT require auth
- CORS restricted to localhost:3000
- SQLAlchemy parameterized queries prevent SQL injection

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Async SQLAlchemy | Non-blocking DB ops, future-proof for high concurrency |
| JSON in TEXT columns | Flexible schema for chart configs and CSV data without migrations |
| Absolute positioning for charts | Simple, predictable, maps 1:1 to drag-drop UX |
| Vite proxy for dev | Avoids CORS issues in development, single origin in production |
| Zustand for auth state | Minimal, no boilerplate, perfect for simple global state |
