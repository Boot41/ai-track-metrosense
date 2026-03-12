from __future__ import annotations

from .backend_client import backend_get
from .types import ToolResult


async def get_aqi_current(location_id: str, limit: int = 1) -> ToolResult:
    return await backend_get(
        "/internal/aqi/current", {"location_id": location_id, "limit": limit}
    )


async def get_aqi_historical(location_id: str, days: int = 365) -> ToolResult:
    return await backend_get(
        "/internal/aqi/historical", {"location_id": location_id, "days": days}
    )


async def get_aqi_summary(location_id: str) -> ToolResult:
    """Monthly AQI aggregates (avg/min/max AQI + dominant category) for a neighbourhood.

    Returns up to 12 rows — one per calendar month. Use this for annual trend
    analysis, year-long summaries, worst-month comparisons, or any question that
    requires aggregating AQI over months rather than individual readings.
    Args:
        location_id: Neighbourhood name exactly as returned by resolve_location
                     (e.g. 'Bellandur', 'Whitefield', 'Koramangala').
    """
    return await backend_get("/internal/aqi/summary", {"location_id": location_id})


async def get_ward_profile(ward_id: str) -> ToolResult:
    return await backend_get("/internal/ward/profile", {"ward_id": ward_id})
