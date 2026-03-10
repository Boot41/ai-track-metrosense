from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings

CHAT_TIMEOUT_SECONDS = 30.0


def _artifact_or_none(payload: dict[str, Any]) -> dict[str, Any] | None:
    artifact = payload.get("artifact")
    if isinstance(artifact, dict):
        return artifact
    return None


def _risk_card_or_none(payload: dict[str, Any]) -> dict[str, Any] | None:
    risk_card = payload.get("risk_card")
    if isinstance(risk_card, dict):
        return risk_card
    return None


async def get_chat_response(settings: Settings, session_id: str, message: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=CHAT_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{settings.agent_server_url.rstrip('/')}/chat",
            json={"session_id": session_id, "message": message},
        )
        response.raise_for_status()
        payload = response.json()

    message_text = payload.get("message")
    if not isinstance(message_text, str):
        raise ValueError("Agent response must include a string 'message'")

    return {
        "message": message_text,
        "risk_card": _risk_card_or_none(payload),
        "artifact": _artifact_or_none(payload),
    }


async def get_agent_health(settings: Settings) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{settings.agent_server_url.rstrip('/')}/health")
        response.raise_for_status()

    return {"backend": "ok", "agent": "ok", "status": "online"}
