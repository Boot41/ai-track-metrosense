from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from ..config import get_settings
from ..prompts import FLOOD_AGENT_INSTRUCTION
from ..tools.flood_tools import get_flood_incidents, get_lake_hydrology
from ..tools.shared.document_tools import fetch_document_section, list_document_indexes
from ..tools.shared.weather_tools import (
    get_weather_current,
    get_weather_extremes,
    get_weather_historical,
    get_weather_summary,
)

_settings = get_settings()

flood_vulnerability_agent = Agent(
    name="flood_vulnerability_agent",
    model=_settings.model,
    description="Flood vulnerability reasoning for Bengaluru zones.",
    instruction=FLOOD_AGENT_INSTRUCTION,
    tools=[
        get_weather_current,
        get_weather_historical,
        get_weather_summary,
        get_weather_extremes,
        get_lake_hydrology,
        get_flood_incidents,
        list_document_indexes,
        fetch_document_section,
    ],
)
