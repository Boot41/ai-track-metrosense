from __future__ import annotations

from ..backend_client import backend_get
from ..types import ToolResult


async def resolve_location(name: str) -> ToolResult:
    return await backend_get("/internal/locations/resolve", {"name": name})


async def list_locations(limit: int = 200) -> ToolResult:
    return await backend_get("/internal/locations", {"limit": limit})
