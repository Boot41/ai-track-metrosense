  Title: Shared Secret Header Protection for Backend → Agents (Dev)

  Summary
  Implement a shared secret header between server/ and agents/ using X-Internal-Token and AGENT_INTERNAL_TOKEN. Add a
  lightweight FastAPI proxy in agents/ that enforces the header on all non-/health routes and forwards requests to
  the ADK server. Keep the backend pointing to 8020 by running the proxy on 8020 and ADK on 8021.

  Key Changes

  1. Backend: config + header injection
      - Add agent_internal_token: str in server/app/core/config.py sourced from AGENT_INTERNAL_TOKEN.
      - In server/app/services/agent_proxy.py, require a non-empty token and send X-Internal-Token on session
        creation, POST /run, and GET /health.
      - Hard-fail if the token is missing/blank (clear error).
  2. Agents: proxy with header enforcement
      - Add a small FastAPI proxy (e.g., agents/app/proxy.py) that:
          - Reads AGENT_INTERNAL_TOKEN and ADK_BASE_URL (default http://127.0.0.1:8021).
          - Allows GET /health without auth.
          - Requires X-Internal-Token for all other routes; returns 401 if missing/invalid.
          - Forwards method, path, query, body, and headers (minus the internal token) to ADK.
      - Run ADK on 8021, proxy on 8020.
      - Update agents dev command/docs to start both processes accordingly.
  3. Tests
      - Update server/tests/integration/agent_stub.py to require X-Internal-Token for all non-/health endpoints.
      - Update server/tests/integration/conftest.py to set AGENT_INTERNAL_TOKEN.
      - Add a unit test in server/tests/unit/test_chat_api.py that verifies missing token produces a clear failure.

  Public Interface/Contract Changes

  - New required env var: AGENT_INTERNAL_TOKEN in both server/ and agents/.
  - Agents proxy accepts X-Internal-Token on all non-/health endpoints.
  - Agents /health remains unauthenticated.

  Test Plan

  1. uv run pytest tests/unit -q (server).
  2. uv run pytest tests/integration -q (server) with the agent stub enforcing the header.
  3. Manual local smoke:
      - Start ADK on 8021, proxy on 8020.
      - Verify backend → proxy → ADK works with the correct header.
      - Verify direct calls to proxy without header get 401.

  Assumptions

  - ADK does not expose an easy middleware hook, so we use a local proxy.
  - Two processes in dev is acceptable (ADK + proxy).
