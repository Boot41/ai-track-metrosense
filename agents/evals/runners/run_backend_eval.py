from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

import httpx

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.backend import ensure_logged_in, run_backend_case
from evals.lib.catalog import dump_json, load_catalog


async def _run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog((repo_root / args.catalog).resolve())
    output_path = (repo_root / args.output).resolve()

    async with httpx.AsyncClient(timeout=args.timeout, follow_redirects=True) as client:
        await ensure_logged_in(
            client,
            base_url=args.base_url.rstrip("/"),
            email=args.email,
            password=args.password,
        )

        results: list[dict[str, object]] = []
        for case in catalog.cases:
            if "backend_e2e" not in case.tier_targets:
                continue
            run_result = await run_backend_case(
                client,
                repo_root=repo_root,
                base_url=args.base_url.rstrip("/"),
                case=case,
            )
            results.append(
                {
                    "case_id": run_result.case_id,
                    "mode": run_result.mode,
                    "session_id": run_result.session_id,
                    "turns": [
                        {
                            "user_message": turn.user_message,
                            "request_session_id": turn.request_session_id,
                            "response_status": turn.response_status,
                            "response_payload": turn.response_payload,
                        }
                        for turn in run_result.turns
                    ],
                    "transcript_payload": run_result.transcript_payload,
                    "fixture_payload": run_result.fixture_payload,
                }
            )

    dump_json(output_path, {"catalog_id": catalog.catalog_id, "results": results})
    print(json.dumps({"output": str(output_path), "result_count": len(results)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MetroSense backend end-to-end eval cases.")
    parser.add_argument("--catalog", required=True, help="Canonical eval catalog JSON path.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="Backend base URL.")
    parser.add_argument("--email", default="evals@example.com", help="Eval user email.")
    parser.add_argument("--password", default="password123", help="Eval user password.")
    parser.add_argument(
        "--output",
        default="agents/evals/results/backend_eval_results.json",
        help="Path to write raw backend eval results JSON.",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
