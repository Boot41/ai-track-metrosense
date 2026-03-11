from __future__ import annotations

from metrosense_agent.prompts import CHAT_AGENT_INSTRUCTION, OFF_DOMAIN_REFUSAL


def test_chat_instruction_contains_refusal_guardrail() -> None:
    assert OFF_DOMAIN_REFUSAL in CHAT_AGENT_INSTRUCTION
