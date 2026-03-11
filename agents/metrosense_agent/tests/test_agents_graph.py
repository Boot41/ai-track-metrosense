from __future__ import annotations

from metrosense_agent.agent import root_agent
from metrosense_agent.subagents import chat_agent


def test_root_agent_identity() -> None:
    assert root_agent.name == "root_agent"


def test_root_has_chat_subagent() -> None:
    subagent_names = [agent.name for agent in getattr(root_agent, "sub_agents", [])]
    assert "chat_agent" in subagent_names
    assert chat_agent.name == "chat_agent"
