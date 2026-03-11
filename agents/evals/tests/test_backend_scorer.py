from __future__ import annotations

from pathlib import Path
import sys

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.backend import CaseRunResult, TurnRunResult
from evals.lib.catalog import load_catalog
from evals.lib.scorer import score_backend_case


def test_score_backend_case_passes_for_valid_payload() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog(repo_root / "agents" / "evals" / "cases" / "core_v1.json")
    case = next(item for item in catalog.cases if item.case_id == "aqi_direct_lookup_001")
    run_result = CaseRunResult(case_id=case.case_id, mode="live", session_id="eval-123")
    run_result.turns.append(
        TurnRunResult(
            user_message=case.conversation[0].user_message,
            request_session_id="eval-123",
            response_status=200,
            response_payload={
                "session_id": "eval-123",
                "response_mode": "text",
                "response_text": "Koramangala AQI is currently Moderate. Freshness note included.",
                "citations_summary": ["get_aqi_current(Koramangala)"],
                "data_freshness_summary": {"note": "Latest AQI observation returned by tool metadata."},
                "risk_card": None,
                "artifact": None,
                "follow_up_prompt": None,
                "message": "Koramangala AQI is currently Moderate. Freshness note included.",
            },
        )
    )
    run_result.transcript_payload = {"messages": [{"role": "user"}, {"role": "assistant"}]}

    scored = score_backend_case(case, run_result)
    assert scored["passed"] is True


def test_score_backend_case_checks_overflow_fixture() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog(repo_root / "agents" / "evals" / "cases" / "session_v1.json")
    case = next(item for item in catalog.cases if item.case_id == "token_overflow_retry_001")
    run_result = CaseRunResult(
        case_id=case.case_id,
        mode="fixture",
        fixture_payload={
            "public_session_id": "s-overflow",
            "backend_trace": {"retry_session_id": "s-overflow--retry-123"},
            "response_payload": {"session_id": "s-overflow"},
        },
    )

    scored = score_backend_case(case, run_result)
    assert scored["passed"] is True
