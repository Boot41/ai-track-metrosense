from __future__ import annotations

import os

import httpx


def main() -> int:
    base_url = os.getenv("SERVER_URL", "http://localhost:8010")
    timeout = httpx.Timeout(30.0)

    with httpx.Client(timeout=timeout) as client:
        # Basic health check — public endpoint, no auth required
        health = client.get(f"{base_url}/health")
        if health.status_code != 200:
            print("health check failed:", health.status_code, health.text)
            return 1

        # Composite health check — verifies backend + agent connectivity
        api_health = client.get(f"{base_url}/api/health")
        if api_health.status_code != 200:
            print("api/health check failed:", api_health.status_code, api_health.text)
            return 1

        payload = api_health.json()
        agent_status = payload.get("agent", "unknown")
        if agent_status == "down":
            print("WARNING: agent is down —", payload)
            # Return 1 only if agent is required for this smoke test
            # In CI without a running agent, treat degraded as a warning
        else:
            print("health ok:", payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
