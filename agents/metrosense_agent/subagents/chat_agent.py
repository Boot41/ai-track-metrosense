from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from ..config import get_settings
from ..prompts import CHAT_AGENT_INSTRUCTION
from ..tools.shared.document_tools import list_document_indexes
from ..tools.shared.location_tools import resolve_location
from .flood_agent import flood_vulnerability_agent
from .heat_agent import heat_health_agent
from .infra_agent import infrastructure_agent
from .logistics_agent import logistics_agent

_settings = get_settings()

chat_agent = Agent(
    name="chat_agent",
    model=_settings.model,
    description="User-facing MetroSense conversational agent.",
    instruction=CHAT_AGENT_INSTRUCTION,
    tools=[resolve_location, list_document_indexes],
    sub_agents=[
        flood_vulnerability_agent,
        heat_health_agent,
        infrastructure_agent,
        logistics_agent,
    ],
)
