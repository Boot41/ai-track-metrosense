# MetroSense

MetroSense is a chat-first climate and infrastructure intelligence system for Bengaluru, built with FastAPI, React, and PostgreSQL. This repo includes the backend, frontend, and internal agents service plus the tooling and quality gates needed to evolve the product.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16 |
| Frontend | React 18, TypeScript, Vite 5, Material-UI v6 |
| Package Managers | uv (Python), pnpm (Node) |
| Quality | Ruff, MyPy (strict), import-linter, ESLint, TypeScript strict |
| Containers | Docker, Docker Compose |
| CI | GitHub Actions |

## Project Structure

```
.
├── .github/workflows/ci.yml    # CI pipeline
├── docker-compose.yml           # PostgreSQL + API + Client
├── Dockerfile                   # Multi-stage production build
├── server/                      # FastAPI backend
│   ├── app/
│   │   ├── api/routes/          # auth, chat, health, internal data routes
│   │   ├── core/                # Config + logging
│   │   ├── db/                  # SQLAlchemy models (10+) + session
│   │   ├── middleware/          # Error handler + request logging
│   │   ├── services/            # agent_proxy, auth, conversation, data_service
│   │   └── main.py              # App factory
│   ├── alembic/                 # Database migrations
│   ├── scripts/
│   │   └── load_metrosense_dataset.py  # CSV data loader (ready, not yet run)
│   ├── DataSet_MetroSense/      # 6 CSVs: weather, AQI, floods, outages, traffic, lakes
│   ├── Documents_Metrosense/    # Reference docs read by agent document_tools
│   ├── tests/                   # Unit + integration tests
│   └── pyproject.toml           # Dependencies + tool config
├── agents/                      # ADK agent service (internal, port 8020/8021)
│   ├── app/proxy.py             # Lightweight proxy enforcing X-Internal-Token
│   ├── metrosense_agent/        # Production agent (5-agent ADK hierarchy)
│   │   ├── agent.py             # root_agent definition
│   │   ├── config.py            # AgentSettings (model, URLs, token, docs path)
│   │   ├── subagents/           # chat, flood, heat, infra, logistics agents
│   │   ├── tools/               # Domain tools calling /internal/* routes
│   │   ├── orchestration/       # routing.py + response_contract.py
│   │   └── prompts/             # System prompts for all five agents
│   ├── metrosearch_agent/       # Legacy Google Search skeleton (can be removed)
│   ├── scripts/smoke_test.py    # Smoke test for backend + agent pipeline
│   └── pyproject.toml           # Dependencies + tool config
└── client/                      # React frontend
    ├── src/
    │   ├── App.tsx              # Router + pages
    │   ├── main.tsx             # Entry point + providers
    │   ├── auth/                # AuthContext + ProtectedRoute
    │   ├── components/chat/     # MessageBubble, MessageList, RiskCard, ArtifactRenderer
    │   ├── components/input/    # InputBar
    │   ├── pages/               # ChatPage, LoginPage, SignupPage
    │   └── lib/api.ts           # Axios instance
    ├── package.json             # Dependencies + scripts
    └── Dockerfile               # Node build → Nginx
```

## Module Boundaries

- `app.api` depends on `app.services`, `app.core` only
- `app.services` depends on `app.db`, `app.core` only (must NOT import from `app.api`)
- `app.db` depends on `app.core` only (must NOT import from `app.services` or `app.api`)
- Enforced by `import-linter` in CI

## Agent Architecture

The agents service runs a five-agent hierarchy built with Google ADK:

```
root_agent
└── chat_agent  (intent routing, location resolution)
    ├── flood_vulnerability_agent  (lake hydrology, flood incidents, weather)
    ├── heat_health_agent          (AQI current/historical, ward profile, weather)
    ├── infrastructure_agent       (power outage events, weather)
    └── logistics_agent            (traffic current/corridor, flood incidents, weather)
```

All agent tools call token-gated `/internal/*` routes on the backend. The proxy on port 8020 enforces `X-Internal-Token` and forwards to the ADK server on port 8021. The frontend never contacts the agent service directly.

## Seeding the Database

Domain data lives in `server/DataSet_MetroSense/` as 6 CSVs (weather, AQI, floods, lake hydrology, outages, traffic). The loader script must be run once before agent tools can return real data:

```bash
cd server
uv run python scripts/load_metrosense_dataset.py --replace
```

Reference documents (`Documents_Metrosense/`) are read directly from the filesystem by the agent; no database import is needed for those.

## Quick Start

The agents service is protected by a shared secret header in dev. The backend calls the proxy on port 8020, which forwards to the ADK server on port 8021. Set the same `AGENT_INTERNAL_TOKEN` in both services.

```bash
# Start PostgreSQL
docker-compose up -d db

# Backend
cd server
uv sync --all-extras
uv run alembic upgrade head
export AGENT_INTERNAL_TOKEN=dev-internal-token
uv run uvicorn app.main:app --reload --port 8010

# (One-time) Seed domain data
uv run python scripts/load_metrosense_dataset.py --replace

# ADK agent server — separate terminal
cd agents
uv sync
export GOOGLE_API_KEY=your_key
export AGENT_INTERNAL_TOKEN=dev-internal-token
export BACKEND_INTERNAL_URL=http://localhost:8010
export DOCUMENTS_PATH=../server/Documents_Metrosense
uv run adk api_server --host 0.0.0.0 --port 8021 .

# Agents proxy — separate terminal
cd agents
export AGENT_INTERNAL_TOKEN=dev-internal-token
uv run uvicorn app.proxy:app --host 0.0.0.0 --port 8020

# Optional: ADK Web UI
cd agents
uv run adk web --port 8001

# Frontend — separate terminal
cd client
pnpm install
pnpm run dev
```

App runs at http://localhost:5173 with API proxied to :8010.

## Quality Gates

Backend (from `server/`):
```bash
uv run ruff format --check .    # Formatting
uv run ruff check .             # Linting
uv run mypy .                   # Type checking (strict)
uv run lint-imports             # Module boundaries
uv run pytest tests/unit -q     # Unit tests
uv run pytest tests/integration -q  # Integration tests
```

Frontend (from `client/`):
```bash
pnpm run lint   # ESLint
pnpm run build  # TypeScript + Vite build
```

Frontend E2E (from `client/`):
```bash
pnpm exec playwright install
pnpm run test:e2e
```

Secrets scanning (from repo root):
```bash
pre-commit install
pre-commit install --hook-type pre-push
gitleaks dir .
```

The repo root pre-commit config includes `gitleaks` hooks for both `pre-commit` and `pre-push`, so secrets are checked before commits and again before pushes. CI also runs the official Gitleaks GitHub Action on the checked-out git history.

## MetroSense Golden Dataset

For the implemented Postgres schema + CSV loader for MetroSense golden data, see:

- `docs/METROSENSE_DATASET_SCHEMA_AND_LOADER.md`

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Basic health check |
| GET | `/api/health` | No | Composite health (backend + agent) |
| POST | `/api/auth/signup` | No | Create account + set JWT cookie |
| POST | `/api/auth/login` | No | Login + set JWT cookie |
| POST | `/api/auth/logout` | Yes | Clear JWT cookie |
| GET | `/api/auth/me` | Yes | Current user |
| POST | `/api/chat` | Yes | Chat request — returns `response_text`, optional `risk_card` and `artifact` |
| GET | `/internal/weather/current` | Token | Current weather by zone (agent use only) |
| GET | `/internal/weather/historical` | Token | Historical weather by zone (agent use only) |
| GET | `/internal/aqi/current` | Token | Current AQI by neighbourhood (agent use only) |
| GET | `/internal/aqi/historical` | Token | Historical AQI by neighbourhood (agent use only) |
| GET | `/internal/lakes` | Token | Lake hydrology records (agent use only) |
| GET | `/internal/floods` | Token | Flood incidents by ward (agent use only) |
| GET | `/internal/outages` | Token | Power outage events by ward (agent use only) |
| GET | `/internal/traffic/current` | Token | Current traffic by zone (agent use only) |
| GET | `/internal/traffic/corridor` | Token | Traffic corridor data (agent use only) |
| GET | `/internal/ward/profile` | Token | Ward demographic/infrastructure profile (agent use only) |
| GET | `/internal/locations` | Token | List all known locations (agent use only) |
| GET | `/internal/locations/resolve` | Token | Resolve location name to canonical record (agent use only) |
| GET | `/internal/aqi/summary` | Token | Monthly AQI aggregates per neighbourhood (agent use only) |
| GET | `/internal/weather/summary` | Token | Monthly weather aggregates per zone (agent use only) |
| GET | `/internal/weather/extremes` | Token | Top N extreme days ranked by temperature or rainfall (agent use only) |
| DELETE | `/api/chat/{session_id}` | Yes | Clear chat session (placeholder — not yet implemented) |

## Environment Variables

### Backend (server/)

| Variable | Default | Description |
|----------|---------|-------------||
| `ENV` | `development` | development / test / production |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/app_scaffold` | Database connection |
| `JWT_SECRET` | `change-me` | JWT signing secret (must be overridden in production — minimum 32 bytes) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRES_MINUTES` | `60` | JWT expiration in minutes |
| `AUTH_COOKIE_NAME` | `metrosense_token` | Auth cookie name |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed origins for cookies |
| `AGENT_INTERNAL_TOKEN` | *(required)* | Shared secret for backend-to-agent proxy authentication |
| `AGENT_SERVER_URL` | `http://agents:8020` | Internal URL for agents proxy (override to `http://localhost:8020` for local dev outside Docker) |

### Agents (agents/)

| Variable | Default | Description |
|----------|---------|-------------||
| `GOOGLE_API_KEY` | *(required)* | Google Generative AI API key for Gemini model |
| `AGENT_INTERNAL_TOKEN` | *(required)* | Shared secret for proxy authentication (must match backend) |
| `AGENT_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `BACKEND_INTERNAL_URL` | `http://localhost:8010` | Backend base URL for internal data routes |
| `DOCUMENTS_PATH` | *(required)* | Filesystem path to `Documents_Metrosense/` directory |
| `ADK_BASE_URL` | `http://localhost:8021` | ADK API server URL (used by proxy) |

## Current Implementation Status

### What Works (✅)
- **Auth:** Signup, login, logout, JWT cookies, password hashing
- **Chat Endpoint:** Routes messages through the five-agent hierarchy; returns structured `ChatResponse` with `response_text`, optional `risk_card`, and `artifact` fields
- **Database:** Schema defined for weather, AQI, flooding, outages, traffic, location master, ward profiles, sessions, and conversation history (10+ models)
- **Internal Data Routes:** All `/internal/*` endpoints (weather, AQI, lakes, floods, outages, traffic, ward, locations) — token-gated and consumed by agent tools
- **Agent Subagents:** Five-agent ADK hierarchy (`root → chat → flood / heat / infra / logistics`) with domain-specific tools calling the backend
- **Agent Tools:** `flood_tools`, `heat_tools`, `infra_tools`, `logistics_tools`, `weather_tools`, `location_tools`, `document_tools` — all wired to backend internal routes
- **Orchestration:** Keyword-based intent routing (`routing.py`) and structured response builder (`response_contract.py`)
- **Backend Services:** `data_service.py` (all domain queries), `conversation_service.py` (session + turn persistence), `agent_proxy.py` (ADK response parsing)
- **Frontend UI:** Chat interface with `MessageBubble`, `MessageList`, `ThinkingIndicator`, `SuggestedPrompts`, login/signup pages, `RiskCard` and `ArtifactRenderer` components
- **Health Checks:** Simple `/health` and composite `/api/health` (backend + agent status)

### What's Missing (📋)
- **Data Loading:** 6 CSVs exist in `DataSet_MetroSense/` but are not yet seeded — run `scripts/load_metrosense_dataset.py --replace` once
- **Structured Risk Card Population:** Schema and contract are end-to-end wired; agent logic needs real data to populate `risk_card` and `artifact` fields
- **Message Context:** `ConversationHistory` is persisted but previous turns are not yet injected back into the agent session
- **Frontend Structured Response Fields:** `ChatResponse` type only reads the backward-compat `message` field; `response_text`, `citations_summary`, `data_freshness_summary`, and `follow_up_prompt` are not yet surfaced in the UI
- **Streaming:** Responses are buffered POST/response; SSE or WebSocket not yet implemented
- **E2E Tests:** Playwright configuration exists but no test suites written yet
- **AuditLog:** Model and table exist but are never written to
- **Session Reset:** `DELETE /api/chat/{session_id}` endpoint is a no-op placeholder

### Next Steps
See **Next Steps (Recommended Order)** in [AGENTS.md](AGENTS.md#next-steps-recommended-order) and the full gap/bug inventory in [AUDIT.md](AUDIT.md) for the development roadmap.

## Docker

```bash
# Development (3 services)
docker-compose up

# Production (single image)
docker build -t metrosense .
```

## Coding Style

- Python: 4-space indent, type hints, `snake_case` functions, `PascalCase` classes
- TypeScript: strict mode, `PascalCase` components, `camelCase` utilities
- Backend layering: Routes → Services → DB (enforced)
- Conventional Commits: `feat:`, `fix:`, `refactor:`
