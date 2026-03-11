from __future__ import annotations

from .backend_client import _get
from .types import ToolResult


async def get_aqi_current(location_id: str, limit: int = 1) -> ToolResult:
    return await _get("/internal/aqi/current", {"location_id": location_id, "limit": limit})


async def get_aqi_historical(location_id: str, days: int = 365) -> ToolResult:
    return await _get("/internal/aqi/historical", {"location_id": location_id, "days": days})


async def get_ward_profile(ward_id: str) -> ToolResult:
    return await _get("/internal/ward/profile", {"ward_id": ward_id})
