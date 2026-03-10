from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings

CHAT_TIMEOUT_SECONDS = 30.0


def _auth_headers(settings: Settings) -> dict[str, str]:
    token = settings.agent_internal_token.strip()
    if not token:
        raise ValueError("AGENT_INTERNAL_TOKEN must be set for agent requests")
    return {"X-Internal-Token": token}


def _extract_message_from_events(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        content = event.get("content")
        if not isinstance(content, dict):
            continue
        role = content.get("role")
        if role not in (None, "model"):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        texts = [
            part.get("text")
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        if texts:
            return "\n".join(texts)
    raise ValueError("Agent response did not include model text")


async def _ensure_session(
    client: httpx.AsyncClient,
    base_url: str,
    app_name: str,
    user_id: str,
    session_id: str,
    headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{base_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}",
        headers=headers,
        json=None,
    )
    if response.status_code in {200, 201, 204, 409}:
        return
    response.raise_for_status()


async def get_chat_response(settings: Settings, session_id: str, message: str) -> dict[str, Any]:
    headers = _auth_headers(settings)
    async with httpx.AsyncClient(timeout=CHAT_TIMEOUT_SECONDS) as client:
        base_url = settings.agent_server_url.rstrip("/")
        app_name = settings.agent_app_name
        user_id = "metrosense"
        await _ensure_session(
            client=client,
            base_url=base_url,
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            headers=headers,
        )
        response = await client.post(
            f"{base_url}/run",
            headers=headers,
            json={
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {"role": "user", "parts": [{"text": message}]},
                "streaming": False,
            },
        )
        response.raise_for_status()
        events = response.json()

    if not isinstance(events, list):
        raise ValueError("Agent response must be a list of events")

    message_text = _extract_message_from_events(events)

    return {
        "message": message_text,
        "risk_card": None,
        "artifact": None,
    }


async def get_agent_health(settings: Settings) -> dict[str, str]:
    headers = _auth_headers(settings)
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{settings.agent_server_url.rstrip('/')}/health",
            headers=headers,
        )
        response.raise_for_status()

    return {"backend": "ok", "agent": "ok", "status": "online"}
