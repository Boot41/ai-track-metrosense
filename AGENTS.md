# AGENTS.md

## Project Identity
- This repository is the working MetroSense codebase: `client/` for React, `server/` for FastAPI, PostgreSQL via Docker Compose, and CI/quality gates.
- The product is `MetroSense`, a chat-based climate and infrastructure intelligence system for Bengaluru.
- The target architecture is a three-service system:
  - `client/`: frontend chat application
  - `server/`: public backend API and orchestration layer
  - `agents/`: internal agent server and tool-execution layer (✅ **exists and wired**, current status: skeleton with google_search tool only)
- Treat the current implementation as the baseline and evolve it toward this three-service design instead of creating parallel app structures.
- **Status**: ~40% complete. Auth flow, backend-to-agent routing, and database schema are functional. Data seeding, custom agent tools, risk cards/artifacts, streaming, and message persistence are planned.

## Canonical Architecture
- The intended request flow is:
  - `frontend -> backend -> agent`
- The frontend should never call the agent service directly.
- `server/` is the only public API boundary for browser clients.
- `agents/` is an internal service boundary responsible for agent runtime behavior, tool usage, and structured chat output generation.
- If existing docs still use `agent/` singular, treat that as referring to the planned `agents/` subsystem until naming is aligned across the repo.

## Why This Boundary Exists
- Keep secrets, database access, internal tools, and agent infrastructure off the public internet.
- Let the backend own request validation, session coordination, auth, rate limiting, logging, and response shaping.
- Preserve a stable frontend contract even if the agent framework, prompting strategy, or toolchain changes.
- Keep observability and failure handling centralized in the backend rather than split between browser and agent server.

## Tech Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, PostgreSQL 16, Loguru, `uv`
- Frontend: React 18, TypeScript, Vite 5, MUI v6, React Query, Zustand, Axios, `pnpm`
- Tooling: Ruff, MyPy strict, import-linter, ESLint, Docker, Docker Compose, GitHub Actions

## Repository Shape
- `client/`
  - Chat UI, streaming presentation, structured response rendering, browser-facing state management.
- `server/`
  - Public HTTP API, request validation, orchestration, session handling, backend-to-agent coordination.
- `agents/`
  - Internal agent service for chat generation, tool calls, retrieval, and domain intelligence.
- `server/app/api/`
  - FastAPI routes and request/response boundaries.
- `server/app/services/`
  - Backend business logic and internal orchestration code.
- `server/app/db/`
  - Database models, metadata, and session management.
- `server/tests/unit/`
  - Fast isolated tests for backend logic and simple route behavior.
- `server/tests/integration/`
  - App-level and database-backed tests.
- `docs/FRONTEND_SPEC.md`
  - Source of truth for the planned MetroSense chat UX and structured response behavior.

## Architectural Rules
- Preserve backend layering:
  - `app.api` may depend on `app.services` and `app.core`
  - `app.services` may depend on `app.db` and `app.core`
  - `app.db` must not depend on `app.services` or `app.api`
- Keep the frontend focused on rendering and interaction, not business orchestration.
- Route all browser chat traffic through `server/`, even after `agents/` exists.
- Treat backend-to-agent communication as an internal interface that may evolve without breaking the UI.
- Prefer extending existing `server/` and `client/` entrypoints over introducing duplicate service layers or alternative public APIs.

## Authentication
- Public endpoints:
  - `POST /api/auth/signup`
  - `POST /api/auth/login`
- Protected endpoints:
  - All other `/api/*` routes require a valid JWT cookie.
- `/health` remains public for uptime checks.

## Product Direction
- MetroSense is intended to be a chat-first application for weather risk, flooding, AQI, outage, traffic, and infrastructure-readiness questions.
- Expected response modes:
  - streamed assistant text for most responses
  - agent-emitted `RiskCard` payloads for structured neighborhood risk outputs
  - agent-emitted `Artifact` payloads for charts, maps, tables, or other visual responses
- Structured outputs should be decided by the agent layer and delivered through the backend to the frontend.
- The frontend must render structured responses based on explicit backend/agent event types, not keyword inference.

## Testing And Validation
- Backend checks from `server/`:
  - `uv sync --all-extras`
  - `uv run ruff format --check .`
  - `uv run ruff check .`
  - `uv run mypy .`
  - `uv run lint-imports`
  - `uv run pytest tests/unit -q`
  - `uv run pytest tests/integration -q`
- Agents checks from `agents/`:
  - `uv sync`
  - `uv run python scripts/smoke_test.py`
- Frontend checks from `client/`:
  - `pnpm install --frozen-lockfile`
  - `pnpm run lint`
  - `pnpm run build`
  - `pnpm exec playwright install`
  - `pnpm run test:e2e`
- Local startup today:
  - The agents service runs behind a lightweight proxy that enforces the `X-Internal-Token` shared secret. The backend calls the proxy on port 8020, and the proxy forwards to the ADK server on port 8021. `/health` stays public for simple availability checks.
  - `docker-compose up -d db`
  - `cd server && export AGENT_INTERNAL_TOKEN=dev-internal-token && uv run alembic upgrade head && uv run uvicorn app.main:app --reload --port 8010`
  - `cd agents && export AGENT_INTERNAL_TOKEN=dev-internal-token && uv run adk api_server --host 0.0.0.0 --port 8021 .`
  - `cd agents && export AGENT_INTERNAL_TOKEN=dev-internal-token && uv run uvicorn app.proxy:app --host 0.0.0.0 --port 8020`
  - `cd agents && uv run adk web --port 8001` (optional UI)
  - `cd client && pnpm install && pnpm run dev`
- When expanding `agents/`, keep startup and validation commands updated in this file.

## Current Coverage And Next-Step Expectations

### Implemented (✅)
- **Backend:** Auth flow (signup/login/logout/me with JWT + httponly cookies), health checks, database schema (9+ models for weather/AQI/flooding/outages/traffic), `/api/chat` endpoint
- **Backend-to-Agent:** Proxy service with `X-Internal-Token` validation, session routing to ADK
- **Frontend:** Chat UI (MessageBubble, MessageList, InputBar), auth context (login/signup/logout), RiskCard and ArtifactRenderer components, health polling
- **Tests:** Auth flow (signup/login/logout), password hashing, health checks, basic chat endpoint

### Planned (📋)
- **Agent Tools:** Custom tools for flood-risk assessment, AQI lookup, outage status, traffic conditions, document retrieval
- **Data Seeding:** Load CSV data (DataSet_MetroSense/) and documents (Documents_Metrosense/) into database
- **Structured Responses:** Risk cards and artifacts emitted by agent layer; backend extracts and shapes for frontend
- **Streaming:** Server-sent events (SSE) or WebSocket for streamed text responses
- **Message Persistence:** Store chat history in database; load conversation context for agents
- **Chat Response Tests:** Extend coverage for agent output parsing, risk card generation, artifact rendering

### Current Test Coverage
- Backend: Health, auth (signup/login/logout/me), password hashing, basic chat routing
- Frontend: Component renders (no E2E tests written yet)
- Agents: smoke_test.py validates proxy routing only (not domain logic)

### Next Steps (Recommended Order)
1. Implement data loader to seed MetroSense CSVs and documents
2. Add custom agent tools (flood-risk, aqi-lookup, outage-status, traffic)
3. Implement structured response generation (risk cards/artifacts from agent)
4. Add message history persistence and context retrieval
5. Implement streaming responses (SSE or WebSocket)
6. Extend test coverage for full end-to-end flows

## Agent Guidance
- Before major implementation work, verify repo truth from `README.md`, `server/pyproject.toml`, `client/package.json`, and `docs/FRONTEND_SPEC.md`.
- Prefer `rg` for search.
- Do not document or reference unimplemented services as if they already exist.
- **Important:** The CSV data files (DataSet_MetroSense/) and documents (Documents_Metrosense/) exist in the repo but are **not yet loaded** into the database. Implement a data loader before building agent tools that depend on MetroSense domain knowledge.
- The agent service skeleton runs and routes to google_search tool, but custom domain tools (flood-risk, aqi, outage, traffic) do not yet exist. Add tools incrementally as matching backend data becomes available.
- If current behavior and MetroSense direction diverge, align new work to the MetroSense direction while keeping transitions explicit and incremental.
