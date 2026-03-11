from __future__ import annotations

import re
from typing import Any

from .backend import CaseRunResult
from .models import MetroSenseEvalCase

_LIVE_RE = re.compile(r"\blive\b", re.IGNORECASE)


def _contains_all(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return all(needle.lower() in lowered for needle in needles)


def _contains_any(items: list[Any], needles: list[str]) -> bool:
    haystack = " ".join(str(item) for item in items).lower()
    return all(needle.lower() in haystack for needle in needles)


def _top_level_contract_ok(payload: dict[str, Any]) -> bool:
    required = {
        "session_id",
        "response_mode",
        "response_text",
        "citations_summary",
        "data_freshness_summary",
        "risk_card",
        "artifact",
        "follow_up_prompt",
        "message",
    }
    return required.issubset(payload.keys())


def score_backend_case(case: MetroSenseEvalCase, run_result: CaseRunResult) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    if run_result.mode == "fixture":
        fixture_payload = run_result.fixture_payload or {}
        retry_session_id = (
            fixture_payload.get("backend_trace", {}).get("retry_session_id")
            if isinstance(fixture_payload.get("backend_trace"), dict)
            else None
        )
        checks["expect_retry_session_suffix_used"] = bool(
            retry_session_id and "--retry-" in str(retry_session_id)
        )
        checks["expect_same_public_session_id"] = (
            fixture_payload.get("public_session_id") == fixture_payload.get("response_payload", {}).get("session_id")
        )
        return {"case_id": case.case_id, "passed": all(checks.values()), "checks": checks}

    final_turn = run_result.turns[-1] if run_result.turns else None
    final_payload = final_turn.response_payload if final_turn else {}
    final_expectation = case.conversation[-1].expectation

    checks["expect_json_schema_valid"] = _top_level_contract_ok(final_payload)
    checks["expected_response_mode"] = (
        final_payload.get("response_mode") == final_expectation.expected_response_mode
    )
    checks["must_include"] = _contains_all(
        str(final_payload.get("response_text", "")), final_expectation.must_include
    )
    checks["must_not_include"] = not any(
        needle.lower() in str(final_payload.get("response_text", "")).lower()
        for needle in final_expectation.must_not_include
    )
    checks["requires_risk_card"] = (
        bool(final_payload.get("risk_card")) if final_expectation.requires_risk_card else True
    )
    checks["requires_artifact"] = (
        bool(final_payload.get("artifact")) if final_expectation.requires_artifact else True
    )
    checks["expected_citations_contains"] = _contains_any(
        list(final_payload.get("citations_summary", [])),
        case.expected.expected_citations_contains,
    )

    freshness_summary = final_payload.get("data_freshness_summary", {})
    checks["expected_freshness_keys"] = isinstance(freshness_summary, dict) and all(
        key in freshness_summary for key in case.expected.expected_freshness_keys
    )

    if case.backend_assertions.expect_no_live_claim:
        checks["expect_no_live_claim"] = not _LIVE_RE.search(
            str(final_payload.get("response_text", ""))
        )
    else:
        checks["expect_no_live_claim"] = True

    if case.backend_assertions.expect_history_persisted:
        messages = (run_result.transcript_payload or {}).get("messages", [])
        checks["expect_history_persisted"] = len(messages) >= len(case.conversation) * 2
    else:
        checks["expect_history_persisted"] = True

    if case.backend_assertions.expect_same_public_session_id:
        session_ids = [turn.response_payload.get("session_id") for turn in run_result.turns]
        checks["expect_same_public_session_id"] = bool(
            session_ids and all(session_id == session_ids[0] for session_id in session_ids)
        )
    else:
        checks["expect_same_public_session_id"] = True

    return {"case_id": case.case_id, "passed": all(checks.values()), "checks": checks}
