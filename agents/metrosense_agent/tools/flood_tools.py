from __future__ import annotations

from .backend_client import _get
from .types import ToolResult


async def get_lake_hydrology(lake_id: str, limit: int = 5) -> ToolResult:
    return await _get("/internal/lakes", {"lake_id": lake_id, "limit": limit})


async def get_flood_incidents(location_id: str, limit: int = 20) -> ToolResult:
    return await _get("/internal/floods", {"location_id": location_id, "limit": limit})
