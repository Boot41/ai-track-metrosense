from __future__ import annotations

import json
import re
import time
from typing import Any
from uuid import uuid4

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import AuditLog
from app.services import conversation_service

CHAT_TIMEOUT_SECONDS = 600.0


def _auth_headers(settings: Settings) -> dict[str, str]:
    token = settings.agent_internal_token.strip()
    if not token:
        raise ValueError("AGENT_INTERNAL_TOKEN must be set for agent requests")
    return {"X-Internal-Token": token}


def _is_input_token_limit_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None or response.status_code != 400:
        return False
    body = response.text.lower()
    return "input token count exceeds the maximum number of tokens allowed" in body


def _overflow_retry_session_id(session_id: str) -> str:
    # Keep the id compact and deterministic enough for log correlation.
    compact_base = session_id[:96]
    return f"{compact_base}--retry-{int(time.time() * 1000)}"


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
            t
            for part in parts
            if isinstance(part, dict) and isinstance((t := part.get("text")), str)
        ]
        if texts:
            return "\n".join(texts)
    raise ValueError("Agent response did not include model text")


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.DOTALL)


def _normalise_freshness(value: Any) -> dict[str, Any]:
    """Ensure data_freshness_summary is always a dict for Pydantic validation."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        return {"note": value}
    return {}


def _strip_fences(text: str) -> str:
    """Return the content inside the first markdown code fence, or the original text."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _synthesize_from_level1(parsed: dict[str, Any]) -> str | None:
    """
    Try to build a human-readable response_text from a Level-1 agent payload
    (fields: agent, status, confidence, data, errors, citations, …).
    Returns None when nothing useful can be extracted.
    """
    errors: list[Any] = parsed.get("errors") or []
    status: str = str(parsed.get("status", ""))
    data = parsed.get("data")

    if errors:
        readable = "; ".join(str(e) for e in errors if e)
        if readable:
            return readable

    if isinstance(data, dict):
        parts = [f"{k}: {v}" for k, v in data.items() if v is not None]
        if parts:
            return ". ".join(parts)
    elif isinstance(data, list) and data:
        return str(data[0])

    agent_name: str = str(parsed.get("agent", "agent"))
    if status:
        return f"{agent_name} returned status: {status}"

    return None


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

    # Strip markdown code fences that LLMs sometimes emit around JSON output.
    json_candidate = _strip_fences(raw_text)

    try:
        parsed = json.loads(json_candidate)
    except json.JSONDecodeError:
        return default_payload

    if not isinstance(parsed, dict):
        return default_payload

    # --- Level-2 shape: has response_text directly ---
    response_text = parsed.get("response_text")
    if isinstance(response_text, str) and response_text.strip():
        return {
            "session_id": session_id,
            "response_mode": parsed.get("response_mode", "text"),
            "response_text": response_text,
            "citations_summary": parsed.get("citations_summary", []),
            "data_freshness_summary": _normalise_freshness(parsed.get("data_freshness_summary")),
            "risk_card": parsed.get("risk_card"),
            "artifact": parsed.get("artifact"),
            "follow_up_prompt": parsed.get("follow_up_prompt"),
            "message": response_text,
        }

    # --- Level-1 shape: agent/status/data/errors/confidence ---
    level1_keys = {"agent", "status", "data", "errors", "confidence", "query_id"}
    if level1_keys & parsed.keys():
        synthesized = _synthesize_from_level1(parsed)
        if synthesized:
            return {
                "session_id": session_id,
                "response_mode": "text",
                "response_text": synthesized,
                "citations_summary": parsed.get("citations", []),
                "data_freshness_summary": _normalise_freshness(parsed.get("data_freshness")),
                "risk_card": None,
                "artifact": None,
                "follow_up_prompt": None,
                "message": synthesized,
            }

    return default_payload


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


async def _run_agent_once(
    client: httpx.AsyncClient,
    base_url: str,
    app_name: str,
    user_id: str,
    session_id: str,
    message: str,
    headers: dict[str, str],
) -> list[dict[str, Any]]:
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
    return events


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
        try:
            events = await _run_agent_once(
                client=client,
                base_url=base_url,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                message=message,
                headers=headers,
            )
        except httpx.HTTPStatusError as exc:
            if not _is_input_token_limit_error(exc):
                raise
            retry_session_id = _overflow_retry_session_id(session_id)
            logger.warning(
                "Agent token limit exceeded for session_id={}; retrying once with adk_session_id={}",
                session_id,
                retry_session_id,
            )
            events = await _run_agent_once(
                client=client,
                base_url=base_url,
                app_name=app_name,
                user_id=user_id,
                session_id=retry_session_id,
                message=message,
                headers=headers,
            )

    message_text = _extract_message_from_events(events)
    response_payload = _parse_level2_payload(message_text, session_id=session_id)
    latency_ms = int((time.perf_counter() - started_at) * 1000)

    try:
        await conversation_service.upsert_session(db_session, session_id=session_id)
        assistant_turn_id = await conversation_service.append_turn(
            db_session,
            session_id=session_id,
            user_message=message,
            assistant_message=response_payload["response_text"],
            agents_invoked=[],
            latency_ms=latency_ms,
        )
        db_session.add(
            AuditLog(
                log_id=str(uuid4()),
                session_id=session_id,
                turn_id=assistant_turn_id,
                query_text=message,
                intent_classified=response_payload.get("response_mode"),
                agents_invoked=[],
                overall_confidence=None,
                data_freshness_lag_seconds=None,
                stale_sources=[],
                error_flag=False,
                error_detail=None,
            )
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
