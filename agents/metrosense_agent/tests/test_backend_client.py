from __future__ import annotations

from typing import Any

import pytest

from metrosense_agent.tools import backend_client


class _FakeResponse:
    status_code = 200
    is_error = False
    text = ""

    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def json(self) -> Any:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *_: object, **__: object) -> None:
        pass

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def get(self, *_: object, **__: object) -> _FakeResponse:
        return _FakeResponse(
            {
                "data": [{"observation_id": "wx-1"}],
                "meta": {
                    "dataset_note": "Weather coverage in result: 2026-03-10 to 2026-03-10.",
                    "available_from": "2026-03-10T00:00:00+00:00",
                    "available_to": "2026-03-10T00:00:00+00:00",
                    "last_updated_at": "2026-03-10T00:00:00+00:00",
                    "record_count_returned": 1,
                    "resolved_location": {"query": "Bellandur", "zone_id": "zone_east"},
                },
            }
        )


@pytest.mark.asyncio
async def test_backend_get_maps_internal_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://backend.local")
    monkeypatch.setenv("AGENT_INTERNAL_TOKEN", "token")
    monkeypatch.setattr(backend_client.httpx, "AsyncClient", _FakeAsyncClient)

    result = await backend_client.backend_get(
        "/internal/weather/current", {"location_id": "x"}
    )

    assert result["data"] == [{"observation_id": "wx-1"}]
    assert result["meta"]["ok"] is True
    assert (
        result["meta"]["dataset_note"]
        == "Weather coverage in result: 2026-03-10 to 2026-03-10."
    )
    assert result["meta"]["last_updated_at"] == "2026-03-10T00:00:00+00:00"
    assert result["meta"]["record_count_returned"] == 1
    assert result["meta"]["resolved_location"] == {
        "query": "Bellandur",
        "zone_id": "zone_east",
    }
