# Integration Test Plan (Frontend + Backend Auth Flow)

## Summary
Add backend integration tests that cover signup, login, chat call (via agent stub), and logout using real Postgres. Add frontend Playwright E2E tests that exercise login, typing/sending a chat message, and logout with auto-started services.

## Backend Integration
- Add a lightweight **agent stub server** that implements:
  - `GET /health` → `{ "agent": "ok" }`
  - `POST /apps/{app_name}/users/{user_id}/sessions/{session_id}` → 200
  - `POST /run` → returns an events list containing a model text response
- Add a test module under `server/tests/integration/`:
  - `POST /api/auth/signup` and verify user row exists.
  - `POST /api/auth/login`, capture auth cookie.
  - `POST /api/chat` with cookie, expect stub response text.
  - `POST /api/auth/logout`, then `/api/chat` returns 401.
- In integration conftest:
  - Set `AGENT_SERVER_URL` to stub server URL.
  - Clear `get_settings` cache before app init.

## Frontend E2E (Playwright)
- Add Playwright to `client/` with config and scripts.
- Test flow:
  - Sign up or log in.
  - Type a message and submit; confirm response renders.
  - Click logout and confirm redirect to `/login`.
- Configure Playwright `webServer` to auto-start:
  - Agent stub server
  - Backend server
  - Frontend dev server

## Test Plan
- Backend: `uv run pytest tests/integration -q` (requires Postgres).
- Frontend: `pnpm run test:e2e` (auto-started services).
