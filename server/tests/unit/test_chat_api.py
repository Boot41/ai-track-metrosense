from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.api.deps import require_user
from app.db.models import User
from app.main import app
from app.services import agent_proxy, conversation_service


@pytest.fixture
def auth_override() -> Generator[None, None, None]:
    app.dependency_overrides[require_user] = lambda: User(
        id=1,
        email="test@example.com",
        password_hash="x",
    )
    yield
    app.dependency_overrides.pop(require_user, None)


@pytest.mark.asyncio
async def test_chat_returns_json_payload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    async def _fake_chat_response(**_: object) -> dict[str, object]:
        return {
            "session_id": "test-session",
            "response_mode": "text",
            "response_text": "Flood risk is elevated tonight.",
            "citations_summary": [],
            "data_freshness_summary": {},
            "follow_up_prompt": None,
            "message": "Flood risk is elevated tonight.",
            "risk_card": {
                "neighborhood": "SARJAPUR ROAD",
                "generated_at": "2026-03-10T12:00:00Z",
                "overall_risk_score": 8.8,
            },
            "artifact": {
                "type": "html",
                "title": "Rainfall Trend",
                "source": "<div>chart</div>",
            },
        }

    monkeypatch.setattr(agent_proxy, "get_chat_response", _fake_chat_response)

    response = await client.post(
        "/api/chat",
        json={
            "session_id": "test-session",
            "message": "What is the flood risk tonight?",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "test-session",
        "response_mode": "text",
        "response_text": "Flood risk is elevated tonight.",
        "citations_summary": [],
        "data_freshness_summary": {},
        "follow_up_prompt": None,
        "message": "Flood risk is elevated tonight.",
        "risk_card": {
            "neighborhood": "SARJAPUR ROAD",
            "generated_at": "2026-03-10T12:00:00Z",
            "overall_risk_score": 8.8,
            "flood_risk": None,
            "power_outage_risk": None,
            "traffic_delay_index": None,
            "health_advisory": None,
            "emergency_readiness": None,
            "rainfall_expected_mm_per_hr": None,
            "rainfall_classification": None,
            "barricade_recommendations": None,
        },
        "artifact": {
            "type": "html",
            "title": "Rainfall Trend",
            "source": "<div>chart</div>",
            "columns": None,
            "rows": None,
            "description": None,
        },
    }


@pytest.mark.asyncio
async def test_chat_accepts_table_artifact_payload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    async def _fake_chat_response(**_: object) -> dict[str, object]:
        return {
            "session_id": "test-session",
            "response_mode": "text",
            "response_text": "Comparison ready.",
            "citations_summary": [],
            "data_freshness_summary": {},
            "follow_up_prompt": None,
            "message": "Comparison ready.",
            "risk_card": None,
            "artifact": {
                "type": "table",
                "title": "Bellandur Weather Comparison",
                "columns": ["Metric", "September 2025", "October 2025"],
                "rows": [["Avg Temperature (C)", 23.3, 24.3]],
                "description": "Monthly comparison",
            },
        }

    monkeypatch.setattr(agent_proxy, "get_chat_response", _fake_chat_response)

    response = await client.post(
        "/api/chat",
        json={
            "session_id": "test-session",
            "message": "Compare Bellandur weather in September and October 2025 in a table",
        },
    )

    assert response.status_code == 200
    assert response.json()["artifact"] == {
        "type": "table",
        "title": "Bellandur Weather Comparison",
        "source": None,
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [["Avg Temperature (C)", 23.3, 24.3]],
        "description": "Monthly comparison",
    }


@pytest.mark.asyncio
async def test_chat_returns_agent_error_payload(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    async def _raise_error(**_: object) -> dict[str, object]:
        raise ValueError("bad payload")

    monkeypatch.setattr(agent_proxy, "get_chat_response", _raise_error)

    response = await client.post(
        "/api/chat",
        json={"session_id": "test-session", "message": "hello"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "AGENT_UNAVAILABLE",
            "message": "The agent service is currently unavailable.",
        }
    }


@pytest.mark.asyncio
async def test_api_health_degraded_when_agent_is_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    async def _fake_health(_: object) -> dict[str, str]:
        return {"backend": "ok", "agent": "down", "status": "degraded"}

    monkeypatch.setattr(agent_proxy, "get_agent_health", _fake_health)

    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "backend": "ok",
        "agent": "down",
        "status": "degraded",
    }


@pytest.mark.asyncio
async def test_list_chat_sessions_returns_summaries(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    session_row = type(
        "SessionRow",
        (),
        {
            "session_id": "s-1",
            "title": "Bellandur flood risk",
            "last_active_at": now,
            "total_turns": 6,
        },
    )()

    async def _fake_list_sessions(**_: object) -> list[object]:
        return [session_row]

    monkeypatch.setattr(conversation_service, "list_sessions", _fake_list_sessions)

    response = await client.get("/api/chat/sessions")
    assert response.status_code == 200
    assert response.json() == {
        "sessions": [
            {
                "session_id": "s-1",
                "title": "Bellandur flood risk",
                "last_active_at": "2026-03-10T12:00:00+00:00",
                "total_turns": 6,
            }
        ]
    }


@pytest.mark.asyncio
async def test_get_chat_session_returns_transcript(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    session_row = type(
        "SessionRow",
        (),
        {"session_id": "s-1", "title": "Flood Q&A", "last_active_at": now},
    )()
    user_msg = type("Msg", (), {"role": "user", "message": "Hi", "timestamp": now})()
    assistant_msg = type("Msg", (), {"role": "assistant", "message": "Hello", "timestamp": now})()

    async def _fake_list_session_messages(**_: object) -> tuple[object, list[object]]:
        return session_row, [user_msg, assistant_msg]

    monkeypatch.setattr(conversation_service, "list_session_messages", _fake_list_session_messages)

    response = await client.get("/api/chat/sessions/s-1")
    assert response.status_code == 200
    assert response.json() == {
        "session_id": "s-1",
        "title": "Flood Q&A",
        "last_active_at": "2026-03-10T12:00:00+00:00",
        "messages": [
            {"role": "user", "message": "Hi", "timestamp": "2026-03-10T12:00:00+00:00"},
            {"role": "assistant", "message": "Hello", "timestamp": "2026-03-10T12:00:00+00:00"},
        ],
    }


@pytest.mark.asyncio
async def test_get_chat_session_returns_not_found_for_missing(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, auth_override: None
) -> None:
    async def _fake_list_session_messages(**_: object) -> tuple[None, list[object]]:
        return None, []

    monkeypatch.setattr(conversation_service, "list_session_messages", _fake_list_session_messages)

    response = await client.get("/api/chat/sessions/missing")
    assert response.status_code == 404
