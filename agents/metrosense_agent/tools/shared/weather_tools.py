from __future__ import annotations

from ..backend_client import backend_get
from ..types import ToolResult


async def get_weather_current(location_id: str, limit: int = 1) -> ToolResult:
    return await backend_get(
        "/internal/weather/current", {"location_id": location_id, "limit": limit}
    )


async def get_weather_historical(location_id: str, hours: int = 720) -> ToolResult:
    return await backend_get(
        "/internal/weather/historical", {"location_id": location_id, "hours": hours}
    )


async def get_weather_summary(location_id: str) -> ToolResult:
    """Monthly weather aggregates (avg/max/min temperature, humidity, rainfall) for a zone.

    Returns up to 12 rows — one per calendar month. Use this for annual trend
    analysis, seasonal comparisons, or questions about weather over months or
    the full year rather than recent readings.
    Args:
        location_id: Neighbourhood name or zone id (e.g. 'Bellandur', 'zone_east').
                     The backend resolves neighbourhoods to zones automatically.
    """
    return await backend_get("/internal/weather/summary", {"location_id": location_id})


async def get_weather_extremes(
    metric: str = "temperature_celsius",
    top_n: int = 10,
) -> ToolResult:
    """Top N extreme days across ALL zones ranked by the chosen metric.

    Use this to answer 'hottest day in 2023', 'which area was hottest',
    or 'wettest day of the year'. Returns date, zone, station name, and value.
    Args:
        metric: 'temperature_celsius' for hottest days (default),
                'rainfall_mm_24hour' for wettest days.
        top_n: How many top days to return (1-50). Default 10.
    """
    return await backend_get(
        "/internal/weather/extremes", {"metric": metric, "top_n": top_n}
    )
