from __future__ import annotations

from typing import Any


def build_level2_response(
    *,
    session_id: str,
    response_text: str,
    response_mode: str = "text",
    citations_summary: list[dict[str, Any]] | None = None,
    data_freshness_summary: dict[str, Any] | None = None,
    risk_card: dict[str, Any] | None = None,
    artifact: dict[str, Any] | None = None,
    follow_up_prompt: str | None = None,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "response_mode": response_mode,
        "response_text": response_text,
        "citations_summary": citations_summary or [],
        "data_freshness_summary": data_freshness_summary or {},
        "risk_card": risk_card,
        "artifact": artifact,
        "follow_up_prompt": follow_up_prompt,
        # Backward-compatible field for current client/server tests.
        "message": response_text,
    }
