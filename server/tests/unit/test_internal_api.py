from __future__ import annotations

from collections.abc import Generator

import pytest
from httpx import AsyncClient

from app.api.deps import db_session, settings
from app.core.config import Settings
from app.main import app
from app.services import data_service


@pytest.fixture
def internal_overrides() -> Generator[None, None, None]:
    async def _db_override() -> object:
        return object()

    app.dependency_overrides[db_session] = _db_override
    app.dependency_overrides[settings] = lambda: Settings(
        agent_internal_token="test-internal-token"
    )
    yield
    app.dependency_overrides.pop(db_session, None)
    app.dependency_overrides.pop(settings, None)


@pytest.mark.asyncio
async def test_internal_requires_token(client: AsyncClient, internal_overrides: None) -> None:
    response = await client.get("/internal/weather/current", params={"location_id": "zone_north"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid internal token"}


@pytest.mark.asyncio
async def test_internal_weather_current_returns_payload(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    internal_overrides: None,
) -> None:
    async def _fake_weather_current(*_: object, **__: object) -> list[dict[str, str]]:
        return [{"observation_id": "wx-1", "location_id": "zone_north"}]

    async def _fake_weather_current_zone(*_: object, **__: object) -> str:
        return "zone_north"

    monkeypatch.setattr(data_service, "get_weather_current", _fake_weather_current)
    monkeypatch.setattr(data_service, "resolve_zone_id", _fake_weather_current_zone)

    response = await client.get(
        "/internal/weather/current",
        params={"location_id": "zone_north", "limit": 1},
        headers={"X-Internal-Token": "test-internal-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == [{"observation_id": "wx-1", "location_id": "zone_north"}]
    assert payload["meta"]["ok"] is True
    assert payload["meta"]["domain"] == "weather_current"
    assert payload["meta"]["record_count_returned"] == 1
    assert payload["meta"]["resolved_location"]["zone_id"] == "zone_north"


@pytest.mark.asyncio
async def test_internal_query_validation(client: AsyncClient, internal_overrides: None) -> None:
    response = await client.get(
        "/internal/weather/current",
        params={"location_id": "zone_north", "limit": 0},
        headers={"X-Internal-Token": "test-internal-token"},
    )
    assert response.status_code == 422
