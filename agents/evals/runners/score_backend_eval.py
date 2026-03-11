from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.backend import CaseRunResult, TurnRunResult
from evals.lib.catalog import dump_json, load_catalog
from evals.lib.scorer import score_backend_case


def _to_case_run_result(raw: dict[str, object]) -> CaseRunResult:
    run_result = CaseRunResult(
        case_id=str(raw["case_id"]),
        mode=str(raw["mode"]),
        session_id=raw.get("session_id") if isinstance(raw.get("session_id"), str) else None,
        transcript_payload=raw.get("transcript_payload")
        if isinstance(raw.get("transcript_payload"), dict)
        else None,
        fixture_payload=raw.get("fixture_payload") if isinstance(raw.get("fixture_payload"), dict) else None,
    )
    for turn in raw.get("turns", []):
        if not isinstance(turn, dict):
            continue
        run_result.turns.append(
            TurnRunResult(
                user_message=str(turn["user_message"]),
                request_session_id=str(turn["request_session_id"]),
                response_status=int(turn["response_status"]),
                response_payload=turn.get("response_payload")
                if isinstance(turn.get("response_payload"), dict)
                else {},
            )
        )
    return run_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Score MetroSense backend eval results.")
    parser.add_argument("--catalog", required=True, help="Canonical eval catalog JSON path.")
    parser.add_argument(
        "--results",
        required=True,
        help="Raw backend eval results JSON path produced by run_backend_eval.py.",
    )
    parser.add_argument(
        "--output",
        default="agents/evals/results/backend_eval_scored.json",
        help="Path to write scored backend eval results.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog((repo_root / args.catalog).resolve())
    raw_results = json.loads((repo_root / args.results).resolve().read_text(encoding="utf-8"))
    scored_results: list[dict[str, object]] = []
    cases_by_id = {case.case_id: case for case in catalog.cases}

    for raw_case in raw_results.get("results", []):
        if not isinstance(raw_case, dict):
            continue
        case_id = str(raw_case["case_id"])
        case = cases_by_id[case_id]
        scored_results.append(score_backend_case(case, _to_case_run_result(raw_case)))

    output_path = (repo_root / args.output).resolve()
    dump_json(
        output_path,
        {
            "catalog_id": catalog.catalog_id,
            "passed": sum(1 for item in scored_results if item["passed"]),
            "total": len(scored_results),
            "results": scored_results,
        },
    )
    print(json.dumps({"output": str(output_path), "total": len(scored_results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
