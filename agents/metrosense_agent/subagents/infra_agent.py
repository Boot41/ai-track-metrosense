from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from ..config import get_settings
from ..prompts import INFRA_AGENT_INSTRUCTION
from ..tools.infra_tools import get_power_outage_events
from ..tools.shared.document_tools import fetch_document_section, list_document_indexes
from ..tools.shared.weather_tools import get_weather_current, get_weather_historical

_settings = get_settings()

infrastructure_agent = Agent(
    name="infrastructure_agent",
    model=_settings.model,
    description="Infrastructure stress and outage risk reasoning.",
    instruction=INFRA_AGENT_INSTRUCTION,
    tools=[
        get_weather_current,
        get_weather_historical,
        get_power_outage_events,
        list_document_indexes,
        fetch_document_section,
    ],
)
