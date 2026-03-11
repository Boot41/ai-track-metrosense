from __future__ import annotations

from ..backend_client import _get
from ..types import ToolResult


async def get_weather_current(location_id: str, limit: int = 1) -> ToolResult:
    return await _get("/internal/weather/current", {"location_id": location_id, "limit": limit})


async def get_weather_historical(location_id: str, hours: int = 720) -> ToolResult:
    return await _get("/internal/weather/historical", {"location_id": location_id, "hours": hours})
