from __future__ import annotations

import os

from google.adk.agents.llm_agent import Agent
from google.adk.tools import google_search

INSTRUCTION = (
    "You are MetroSense, a Bengaluru climate and infrastructure intelligence assistant. "
    "Answer concisely, cite sources when possible, and focus on actionable risk insights."
)

root_agent = Agent(
    name="metrosearch_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash"),
    description="MetroSense search-enabled agent for Bengaluru climate and infrastructure queries.",
    instruction=INSTRUCTION,
    tools=[google_search],
)
