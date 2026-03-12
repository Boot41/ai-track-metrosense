from __future__ import annotations

from metrosense_agent.agent import root_agent
from metrosense_agent.subagents import chat_agent


def test_root_agent_identity() -> None:
    assert root_agent.name == "root_agent"


def test_root_has_chat_subagent() -> None:
    subagent_names = [agent.name for agent in getattr(root_agent, "sub_agents", [])]
    assert "chat_agent" in subagent_names
    assert chat_agent.name == "chat_agent"


def test_chat_agent_exposes_prompt_referenced_core_tools() -> None:
    tool_names = {tool.name for tool in getattr(chat_agent, "tools", [])}
    assert "resolve_location" in tool_names
    assert "list_document_indexes" in tool_names
    assert "get_weather_summary" not in tool_names
    assert "get_aqi_summary" not in tool_names
    assert "get_flood_incidents" not in tool_names
    assert "get_power_outage_events" not in tool_names
    assert "get_traffic_corridor" not in tool_names
