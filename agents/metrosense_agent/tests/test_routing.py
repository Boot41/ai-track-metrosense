from __future__ import annotations

from metrosense_agent.orchestration.routing import classify_intents, determine_response_mode


def test_classify_multi_domain_query() -> None:
    intent = classify_intents("If heavy rain hits ORR, what flood and traffic risk should we expect?")
    assert intent.flood is True
    assert intent.logistics is True


def test_scorecard_mode_detection() -> None:
    assert determine_response_mode("Give me a vulnerability scorecard for Bellandur") == "scorecard"
