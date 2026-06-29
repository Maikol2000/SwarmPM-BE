# SwarmPM Mike L. Backend Scaffold

FastAPI scaffold aligned to your assigned milestones:

- `DASH-01` Messages backend (WebSocket chat, presence, unread, history)
- `DASH-04` Spaces API (categories/subcategories)
- `DASH-07` Unified dashboard data endpoint
- `Q-BE-01` JWT auth + role/scope authorization dependencies
- `Q-BE-02` Core business logic service
- `TM-01` Position assignment service
- `TM-04` Workload balancing engine
- `AURA-01` Insight generation service
- `AURA-02` Ask-AURA assistant endpoint
- `TT-01` Point-in-time state snapshots

## 1) Quick start

```powershell
cd "d:\GoBig.app, LLC\swarmpm-mike-backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open: `http://127.0.0.1:8000/docs`

## 2) Auth and authorization for protected APIs

Get a token:

```http
POST /api/auth/token
Content-Type: application/json

{
  "user_id": "mike",
  "role": "manager",
  "scopes": ["chat:read", "chat:write", "spaces:read", "dashboard:read", "team:write", "aura:use", "state:read", "state:write"]
}
```

Use header on protected endpoints:

- `Authorization: Bearer <access_token>`

Compatibility mode remains enabled by default:

- `Authorization: Bearer dev-token`

## 3) Milestone API map

- `DASH-01`
  - `GET /api/chat/history`
  - `GET /api/chat/unread`
  - `PATCH /api/chat/messages/{message_id}/read`
  - `GET /api/chat/presence`
  - `PUT /api/chat/presence`
  - `WS /api/chat/ws?user_id=...&token=...`
- `DASH-04`
  - `GET /api/spaces/categories`
- `DASH-07`
  - `GET /api/dashboard/unified`
- `Q-BE-01`
  - JWT token issue endpoint in `app/api/routes/auth.py`
  - Scope and role dependencies in `app/core/dependencies.py`
  - Token validation and WebSocket auth in `app/core/security.py`
- `Q-BE-02`
  - Shared logic in `app/services/core_logic.py`
- `TM-01`
  - `POST /api/team/assign`
- `TM-04`
  - `POST /api/team/rebalance`
- `AURA-01`
  - `POST /api/aura/insights`
- `AURA-02`
  - `POST /api/aura/ask`
- `TT-01`
  - `POST /api/state/snapshot`
  - `GET /api/state/snapshot/{snapshot_id}`

## 4) Run tests

```powershell
pytest -q
```

## 5) Notes

- This is a production-oriented scaffold, not final business logic.
- Chat and snapshot data are now persisted through SQLAlchemy repositories.
- Default local DB is SQLite (`sqlite:///./swarm.db`).
- Set `DATABASE_URL` to switch to Postgres without changing route/service code.
- Default connection string targets local PostgreSQL 18:

```powershell
postgresql+psycopg://postgres@localhost:5432/postgres
```

## 5.1) PostgreSQL configuration

Use env var before starting the app:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/swarmpm"
uvicorn app.main:app --reload
```

Notes:

- If `DATABASE_URL` is not set, app falls back to SQLite.
- History/unread/mark-read all use the same SQLAlchemy repository and will write/read from PostgreSQL when this env var is set.

## 5.2) Presence tracking behavior

- Presence states are tracked as `online/away/busy/offline`.
- WS connect sets user to `online`, WS disconnect sets `offline`.
- `PUT /api/chat/presence` allows manual status updates (`away`, `busy`, `online`, `offline`).
- Presence is persisted in the database table `presence` via SQLAlchemy.
- With PostgreSQL configured, presence state is shared across app instances.
- If you change `pg_hba.conf`, restart the PostgreSQL 18 service as Administrator so the auth changes take effect.

## 6) Extensible structure

- `app/core`: configuration, security, and auth dependencies
- `app/db`: engine/session initialization
- `app/models`: SQLAlchemy entities
- `app/repositories`: persistence/query logic
- `app/services`: business logic
- `app/api/routes`: HTTP and WebSocket endpoints
