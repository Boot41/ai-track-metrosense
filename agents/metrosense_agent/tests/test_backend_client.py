from __future__ import annotations

import pytest

from metrosense_agent.tools.backend_client import backend_get


@pytest.mark.asyncio
async def test_backend_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND_INTERNAL_URL", raising=False)
    monkeypatch.delenv("AGENT_INTERNAL_TOKEN", raising=False)

    result = await backend_get("/internal/weather/current", {"location_id": "loc_001"})
    assert result["meta"]["ok"] is False
    assert result["meta"]["error_code"] == "BACKEND_CONFIG_MISSING"
