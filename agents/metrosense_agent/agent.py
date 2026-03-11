from __future__ import annotations

from google.adk.agents.llm_agent import Agent

from .config import get_settings
from .prompts import ROOT_AGENT_INSTRUCTION
from .subagents import chat_agent

_settings = get_settings()

root_agent = Agent(
    name="root_agent",
    model=_settings.model,
    description="MetroSense root orchestrator that delegates to chat_agent.",
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[chat_agent],
)
