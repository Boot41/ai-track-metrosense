from __future__ import annotations

from .backend_client import _get
from .types import ToolResult


async def get_power_outage_events(location_id: str, window_days: int = 30) -> ToolResult:
    return await _get("/internal/outages", {"location_id": location_id, "window_days": window_days})
