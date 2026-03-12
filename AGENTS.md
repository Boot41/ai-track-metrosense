# AGENTS.md

## Project Identity
- This repository is the working MetroSense codebase: `client/` for React, `server/` for FastAPI, PostgreSQL via Docker Compose, and CI/quality gates.
- The product is `MetroSense`, a chat-based climate and infrastructure intelligence system for Bengaluru.
- The target architecture is a three-service system:
  - `client/`: frontend chat application
  - `server/`: public backend API and orchestration layer
  - `agents/`: internal agent server and tool-execution layer (✅ **exists and wired**, current status: skeleton with google_search tool only)
- Treat the current implementation as the baseline and evolve it toward this three-service design instead of creating parallel app structures.
- **Status**: ~70% complete. Auth flow, backend-to-agent routing, database schema, internal data routes, custom domain agent tools, structured response contract, and full subagent hierarchy are functional. Data seeding (script ready, not yet run), streaming, and E2E tests remain.

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
- **Backend:** Auth flow (signup/login/logout/me with JWT + httponly cookies), health checks, database schema (10+ models for weather/AQI/flooding/outages/traffic, sessions, conversation history), `/api/chat` endpoint with full `RiskCardPayload` and `ArtifactPayload` response schema
- **Backend Internal Routes:** All `/internal/*` data routes (weather, AQI, lakes, floods, outages, traffic, ward profile, locations) — token-gated, consumed only by agent tools
- **Backend Services:** `data_service.py` (all domain DB queries + neighbourhood→zone mapping), `conversation_service.py` (session upsert + turn append to `ConversationHistory`), `agent_proxy.py` (Level-2 and Level-1 ADK response parsing)
- **Backend-to-Agent:** Proxy service with `X-Internal-Token` validation, session routing to ADK
- **Agent Subagent Hierarchy:** Five-agent system (`root_agent → chat_agent → flood_vulnerability_agent / heat_health_agent / infrastructure_agent / logistics_agent`) using `gemini-2.5-flash`
- **Agent Tools:** `flood_tools` (lake hydrology, flood incidents), `heat_tools` (AQI current/historical, ward profile), `infra_tools` (power outage events), `logistics_tools` (traffic current/corridor), `shared/weather_tools` (weather current/historical), `shared/location_tools` (resolve/list locations), `shared/document_tools` (list indexes, fetch section)
- **Orchestration:** `routing.py` (keyword-based intent classification: flood/heat/infra/logistics/greeting), `response_contract.py` (`build_level2_response()` structured output builder)
- **Prompts:** Domain-specific system prompts for all five agents; `CHAT_AGENT_INSTRUCTION` mandates JSON-only structured output with data freshness caveats and off-domain refusal
- **Data Loader Script:** `server/scripts/load_metrosense_dataset.py` — reads 6 CSVs and inserts reference + domain tables; run with `uv run python scripts/load_metrosense_dataset.py --replace` (not yet executed)
- **Frontend:** Chat UI (MessageBubble, MessageList, InputBar, ThinkingIndicator, SuggestedPrompts), auth context (login/signup/logout), RiskCard and ArtifactRenderer components, health polling
- **Tests:** Auth flow (signup/login/logout/me), password hashing, health checks, basic chat endpoint

### Planned (📋)
- **Data Seeding:** `load_metrosense_dataset.py` exists and is ready to run; CSVs not yet loaded into PostgreSQL — run once before agent tools can return real data
- **Document Ingestion:** Reference documents (`Documents_Metrosense/`) are read directly from the filesystem by `document_tools`; no DB ingestion needed
- **Streaming:** Responses are buffered POST/response; SSE or WebSocket streaming not yet implemented
- **Message Context Loading:** `ConversationHistory` model and `conversation_service` exist; conversation context not yet injected into agent session on new requests
- **Structured Risk Card Generation:** End-to-end schema is wired (`RiskCardPayload` in routes, `build_level2_response()` in agents); requires data seeding + agent logic to populate fields
- **E2E Tests:** Playwright configured; no test suites written yet
- **Chat Response Tests:** Coverage for agent output parsing, risk card generation, artifact rendering

### Current Test Coverage
- Backend: Health, auth (signup/login/logout/me), password hashing, basic chat routing
- Frontend: Component renders (no E2E tests written yet)
- Agents: smoke_test.py validates proxy routing only (not domain logic)

### Next Steps (Recommended Order)
1. **Run data loader** — `cd server && uv run python scripts/load_metrosense_dataset.py --replace` to seed CSVs into PostgreSQL so agent tools return real data
2. **Validate agent tool responses** — Smoke-test each domain tool end-to-end (internal routes → data_service → PostgreSQL) after seeding
3. **Wire conversation context** — Pass recent `ConversationHistory` turns to the agent session so the agent has chat memory
4. **Validate structured output** — Confirm `build_level2_response()` + `RiskCardPayload` round-trip produces renderable frontend cards
5. **Implement streaming** — Add SSE or WebSocket to `/api/chat` for incremental text delivery
6. **Write E2E tests** — Playwright suites covering login → chat → risk card render

## Agent Guidance
- Before major implementation work, verify repo truth from `README.md`, `server/pyproject.toml`, `client/package.json`, and `docs/FRONTEND_SPEC.md`.
- Prefer `rg` for search.
- Do not document or reference unimplemented services as if they already exist.
- **Important:** The CSV data files (`DataSet_MetroSense/`) exist in the repo and the loader script (`server/scripts/load_metrosense_dataset.py`) is implemented but **not yet run**. Seed the database before expecting agent domain tools to return real data.
- Documents (`Documents_Metrosense/`) are served directly from the filesystem by `document_tools` — no DB load needed, but `DOCUMENTS_PATH` env must point to the correct directory.
- The `metrosense_agent/` is the production agent; `metrosearch_agent/` is a legacy skeleton that can be removed. All five subagents and their domain tools are implemented and wired into the ADK hierarchy.
- The `response_contract.py` `build_level2_response()` builder and all Pydantic schemas (`RiskCardPayload`, `ArtifactPayload`) are in place end-to-end — the remaining gap is data availability and agent logic populating those fields.
- If current behavior and MetroSense direction diverge, align new work to the MetroSense direction while keeping transitions explicit and incremental.
