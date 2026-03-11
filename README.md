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
| POST | `/api/chat` | Yes | Chat request |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `development` | development / test / production |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/app_scaffold` | Database connection |
| `JWT_SECRET` | `app-scaffold-dev-secret` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRES_MINUTES` | `60` | JWT expiration in minutes |
| `AUTH_COOKIE_NAME` | `metrosense_token` | Auth cookie name |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed origins for cookies |

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
