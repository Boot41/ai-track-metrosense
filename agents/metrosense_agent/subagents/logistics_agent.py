from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from ..config import get_settings
from ..prompts import LOGISTICS_AGENT_INSTRUCTION
from ..tools.flood_tools import get_flood_incidents
from ..tools.logistics_tools import get_traffic_corridor, get_traffic_current
from ..tools.shared.document_tools import fetch_document_section, list_document_indexes
from ..tools.shared.weather_tools import get_weather_current

_settings = get_settings()

logistics_agent = Agent(
    name="logistics_agent",
    model=_settings.model,
    description="Traffic and logistics disruption reasoning for Bengaluru corridors.",
    instruction=LOGISTICS_AGENT_INSTRUCTION,
    tools=[
        get_traffic_current,
        get_traffic_corridor,
        get_weather_current,
        get_flood_incidents,
        list_document_indexes,
        fetch_document_section,
    ],
)
