from __future__ import annotations

from pathlib import Path
import sys

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.adk import build_eval_config, build_eval_set
from evals.lib.catalog import load_catalog


def test_build_eval_set_preserves_case_ids_and_tool_uses() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog(repo_root / "agents" / "evals" / "cases" / "core_v1.json")
    eval_set = build_eval_set(catalog)

    assert eval_set["eval_set_id"] == "core_v1"
    assert len(eval_set["eval_cases"]) == 20
    aqi_case = next(item for item in eval_set["eval_cases"] if item["eval_id"] == "aqi_direct_lookup_001")
    tool_uses = aqi_case["conversation"][0]["intermediate_data"]["tool_uses"]
    assert [item["name"] for item in tool_uses] == ["resolve_location", "get_aqi_current"]


def test_build_eval_config_contains_adk_metrics() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog(repo_root / "agents" / "evals" / "cases" / "core_v1.json")
    config = build_eval_config(repo_root, catalog)

    criteria = config["criteria"]
    assert "final_response_match_v2" in criteria
    assert "rubric_based_final_response_quality_v1" in criteria
    assert "tool_trajectory_avg_score" in criteria
    assert criteria["tool_trajectory_avg_score"]["matchType"] == "IN_ORDER"
