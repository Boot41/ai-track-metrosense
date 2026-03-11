from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from ..config import get_settings
from ..prompts import HEAT_AGENT_INSTRUCTION
from ..tools.heat_tools import get_aqi_current, get_aqi_historical, get_ward_profile
from ..tools.shared.document_tools import fetch_document_section, list_document_indexes
from ..tools.shared.weather_tools import get_weather_current

_settings = get_settings()

heat_health_agent = Agent(
    name="heat_health_agent",
    model=_settings.model,
    description="Heat and health risk reasoning for Bengaluru neighborhoods.",
    instruction=HEAT_AGENT_INSTRUCTION,
    tools=[
        get_aqi_current,
        get_aqi_historical,
        get_weather_current,
        get_ward_profile,
        list_document_indexes,
        fetch_document_section,
    ],
)
