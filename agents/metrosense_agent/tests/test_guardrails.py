from __future__ import annotations

from metrosense_agent.prompts import (
    CHAT_AGENT_INSTRUCTION,
    GREETING_INTRO,
    OFF_DOMAIN_REFUSAL,
)


def test_chat_instruction_contains_refusal_guardrail() -> None:
    assert OFF_DOMAIN_REFUSAL in CHAT_AGENT_INSTRUCTION


def test_chat_instruction_contains_greeting_intro_rule() -> None:
    assert GREETING_INTRO in CHAT_AGENT_INSTRUCTION
    assert (
        "If the message includes both greeting and a real question"
        in CHAT_AGENT_INSTRUCTION
    )
