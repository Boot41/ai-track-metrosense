from __future__ import annotations

import pytest

from metrosense_agent.tools.flood_tools import get_flood_incidents
from metrosense_agent.tools.heat_tools import get_aqi_current
from metrosense_agent.tools.infra_tools import get_power_outage_events
from metrosense_agent.tools.logistics_tools import get_traffic_current
from metrosense_agent.tools.shared.location_tools import resolve_location
from metrosense_agent.tools.shared.weather_tools import get_weather_current


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_call",
    [
        lambda: get_weather_current("loc_001"),
        lambda: resolve_location("Bellandur"),
        lambda: get_flood_incidents("loc_001"),
        lambda: get_aqi_current("loc_001"),
        lambda: get_power_outage_events("loc_001"),
        lambda: get_traffic_current("loc_001"),
    ],
)
async def test_domain_tools_return_contract(
    monkeypatch: pytest.MonkeyPatch,
    tool_call,
) -> None:
    monkeypatch.delenv("BACKEND_INTERNAL_URL", raising=False)
    monkeypatch.delenv("AGENT_INTERNAL_TOKEN", raising=False)

    result = await tool_call()
    assert "data" in result
    assert "meta" in result
    assert result["meta"]["ok"] is False
