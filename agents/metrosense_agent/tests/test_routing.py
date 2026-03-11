from __future__ import annotations

from metrosense_agent.orchestration.routing import (
    classify_intents,
    determine_response_mode,
    is_greeting_only,
)


def test_classify_multi_domain_query() -> None:
    intent = classify_intents(
        "If heavy rain hits ORR, what flood and traffic risk should we expect?"
    )
    assert intent.flood is True
    assert intent.logistics is True


def test_scorecard_mode_detection() -> None:
    assert (
        determine_response_mode("Give me a vulnerability scorecard for Bellandur")
        == "scorecard"
    )


def test_greeting_only_detection_true() -> None:
    assert is_greeting_only("Hello there!") is True
    assert is_greeting_only("Good morning") is True


def test_greeting_plus_question_detection_false() -> None:
    assert is_greeting_only("Hi, what is flood risk in Bellandur tonight?") is False
