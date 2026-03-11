from __future__ import annotations

import time
import json
from typing import Any

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.services import conversation_service

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


def _parse_level2_payload(raw_text: str, session_id: str) -> dict[str, Any]:
    default_payload: dict[str, Any] = {
        "session_id": session_id,
        "response_mode": "text",
        "response_text": raw_text,
        "citations_summary": [],
        "data_freshness_summary": {},
        "risk_card": None,
        "artifact": None,
        "follow_up_prompt": None,
        # Backward-compatible field for existing callers.
        "message": raw_text,
    }

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return default_payload

    if not isinstance(parsed, dict):
        return default_payload

    response_text = parsed.get("response_text")
    if not isinstance(response_text, str) or not response_text.strip():
        return default_payload

    return {
        "session_id": session_id,
        "response_mode": parsed.get("response_mode", "text"),
        "response_text": response_text,
        "citations_summary": parsed.get("citations_summary", []),
        "data_freshness_summary": parsed.get("data_freshness_summary", {}),
        "risk_card": parsed.get("risk_card"),
        "artifact": parsed.get("artifact"),
        "follow_up_prompt": parsed.get("follow_up_prompt"),
        "message": response_text,
    }


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


async def get_chat_response(
    settings: Settings,
    db_session: AsyncSession,
    session_id: str,
    message: str,
) -> dict[str, Any]:
    started_at = time.perf_counter()
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
    response_payload = _parse_level2_payload(message_text, session_id=session_id)
    latency_ms = int((time.perf_counter() - started_at) * 1000)

    try:
        await conversation_service.upsert_session(db_session, session_id=session_id)
        await conversation_service.append_turn(
            db_session,
            session_id=session_id,
            user_message=message,
            assistant_message=response_payload["response_text"],
            agents_invoked=[],
            latency_ms=latency_ms,
        )
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        logger.exception("Failed to persist conversation history for session_id={}", session_id)

    return response_payload


async def get_agent_health(settings: Settings) -> dict[str, str]:
    headers = _auth_headers(settings)
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{settings.agent_server_url.rstrip('/')}/health",
            headers=headers,
        )
        response.raise_for_status()

    return {"backend": "ok", "agent": "ok", "status": "online"}
