from __future__ import annotations

import os
import sys

import httpx


def main() -> int:
    base_url = os.getenv("SERVER_URL", "http://localhost:8010")
    timeout = httpx.Timeout(30.0)

    with httpx.Client(timeout=timeout) as client:
        health = client.get(f"{base_url}/api/health")
        if health.status_code != 200:
            print("health check failed:", health.status_code, health.text)
            return 1

        chat = client.post(
            f"{base_url}/api/chat",
            json={"session_id": "smoke-test", "message": "What is Bengaluru's flood risk today?"},
        )
        if chat.status_code != 200:
            print("chat request failed:", chat.status_code, chat.text)
            return 1

        payload = chat.json()
        if "message" not in payload:
            print("chat response missing message:", payload)
            return 1

        print("health ok:", health.json())
        print("chat ok:", payload["message"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
