from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.api.deps import require_user
from app.db.models import User
from app.main import app
from app.services import agent_proxy


@pytest.fixture
def auth_override() -> None:
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
        },
        "artifact": {
            "type": "html",
            "title": "Rainfall Trend",
            "source": "<div>chart</div>",
            "description": None,
        },
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
