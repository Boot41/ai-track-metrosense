from __future__ import annotations

from .backend_client import backend_get
from .types import ToolResult


async def get_traffic_current(location_id: str, limit: int = 5) -> ToolResult:
    return await backend_get(
        "/internal/traffic/current", {"location_id": location_id, "limit": limit}
    )


async def get_traffic_corridor(corridor_name: str, limit: int = 20) -> ToolResult:
    return await backend_get(
        "/internal/traffic/corridor", {"corridor_name": corridor_name, "limit": limit}
    )
