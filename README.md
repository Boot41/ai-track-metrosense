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
│   │   ├── api/routes/          # HTTP endpoints
│   │   ├── core/                # Config + logging
│   │   ├── db/                  # SQLAlchemy models + session
│   │   ├── middleware/          # Error handler + request logging
│   │   ├── services/            # Business logic layer
│   │   └── main.py              # App factory
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Unit + integration tests
│   └── pyproject.toml           # Dependencies + tool config
├── agents/                      # ADK agent service (internal)
│   ├── metrosearch_agent/        # Simple Google Search-enabled agent
│   ├── scripts/                 # Smoke tests
│   └── pyproject.toml           # Dependencies + tool config
└── client/                      # React frontend
    ├── src/
    │   ├── App.tsx              # Router + pages
    │   ├── main.tsx             # Entry point + providers
    │   └── lib/api.ts           # Axios instance
    ├── package.json             # Dependencies + scripts
    └── Dockerfile               # Node build → Nginx
```

## Module Boundaries

- `app.api` depends on `app.services`, `app.core` only
- `app.services` depends on `app.db`, `app.core` only (must NOT import from `app.api`)
- `app.db` depends on `app.core` only (must NOT import from `app.services` or `app.api`)
- Enforced by `import-linter` in CI

## Quick Start

The agents service is protected by a shared secret header in dev. The backend talks to an agents proxy on port 8020, and that proxy forwards to the ADK server on port 8021. Set the same `AGENT_INTERNAL_TOKEN` in both services so the proxy can validate requests.

```bash
# Start PostgreSQL
docker-compose up -d db

# Backend
cd server
uv sync --all-extras
uv run alembic upgrade head
export AGENT_INTERNAL_TOKEN=dev-internal-token
uv run uvicorn app.main:app --reload --port 8010

# Agents (separate terminals)
cd agents
uv sync
export GOOGLE_API_KEY=your_key
export AGENT_INTERNAL_TOKEN=dev-internal-token
uv run adk api_server --host 0.0.0.0 --port 8021 .

# Agents proxy (separate terminal)
cd agents
export AGENT_INTERNAL_TOKEN=dev-internal-token
uv run uvicorn app.proxy:app --host 0.0.0.0 --port 8020

# Optional: ADK Web UI (separate terminal)
cd agents
uv run adk web --port 8001

# Frontend (separate terminal)
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

## MetroSense Golden Dataset

For the implemented Postgres schema + CSV loader for MetroSense golden data, see:

- `docs/METROSENSE_DATASET_SCHEMA_AND_LOADER.md`

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/api/auth/signup` | No | Create account + set JWT cookie |
| POST | `/api/auth/login` | No | Login + set JWT cookie |
| POST | `/api/auth/logout` | Yes | Clear JWT cookie |
| GET | `/api/auth/me` | Yes | Current user |
| POST | `/api/chat` | Yes | Chat request (currently returns text-only; risk cards and artifacts are planned) |

**Note:** The `/api/chat` endpoint currently routes requests to the agent service and retumns streamed or buffered text responses. Risk card and artifact generation (structured responses) are planned and will be implemented once the agent layer is equipped with domain tools and data access.

## Environment Variables

### Backend (server/)

| Variable | Default | Description |
|----------|---------|-------------||
| `ENV` | `development` | development / test / production |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/app_scaffold` | Database connection |
| `JWT_SECRET` | `app-scaffold-dev-secret` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRES_MINUTES` | `60` | JWT expiration in minutes |
| `AUTH_COOKIE_NAME` | `metrosense_token` | Auth cookie name |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed origins for cookies |
| `AGENT_INTERNAL_TOKEN` | *(required)* | Shared secret for backend-to-agent proxy authentication (e.g., `dev-internal-token` in dev) |
| `AGENT_SERVER_URL` | `http://localhost:8020` | Internal URL for agents proxy |

### Agents (agents/)

| Variable | Default | Description |
|----------|---------|-------------||
| `GOOGLE_API_KEY` | *(required)* | Google Generative AI API key for Gemini model |
| `AGENT_INTERNAL_TOKEN` | *(required)* | Shared secret for proxy authentication (must match backend) |
| `AGENT_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `ADK_BASE_URL` | `http://localhost:8021` | (optional) ADK API server URL |

## Current Implementation Status

### What Works (✅)
- **Auth:** Signup, login, logout, JWT cookies, password hashing
- **Chat Endpoint:** Routes messages to agent service; returns text responses
- **Database:** Schema defined for weather, AQI, flooding, outages, traffic, and location data
- **Backend-to-Agent Proxy:** Validates X-Internal-Token, forwards sessions to ADK
- **Frontend UI:** Chat interface, login/signup, message display, component stubs for RiskCard and Artifacts
- **Health Checks:** Backend and composite backend+agent status endpoints

### What's Missing (📋)
- **Data Loading:** CSV files and documents exist but are not yet seeded into PostgreSQL
- **Agent Tools:** Only google_search available; custom flood-risk, AQI, outage, and traffic tools not yet implemented
- **Structured Responses:** Risk cards and artifacts are rendered in UI templates but not yet generated by agent
- **Streaming:** Responses are single POST/response; SSE or WebSocket streaming not yet implemented
- **Message History:** Conversations stored in-memory only; database persistence not yet implemented
- **E2E Tests:** Playwright configuration exists but test suites not written

### Next Steps
See **Next Steps (Recommended Order)** in [AGENTS.md](AGENTS.md#next-steps-recommended-order) for the development roadmap.

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
