from __future__ import annotations

from metrosense_agent.orchestration.response_contract import build_level2_response


def test_l2_response_contains_canonical_and_compat_fields() -> None:
    payload = build_level2_response(session_id="s1", response_text="hello")
    assert payload["response_text"] == "hello"
    assert payload["message"] == "hello"
    assert payload["response_mode"] == "text"
