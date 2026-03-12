from __future__ import annotations

import json
from pathlib import Path
import re

AGENTS_DIR = Path(__file__).resolve().parents[2]


def test_all_eval_assets_are_single_case_evalsets() -> None:
    eval_files = sorted((AGENTS_DIR / "evals" / "adk").rglob("*.test.json"))
    assert eval_files

    for path in eval_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict), path.name
        assert isinstance(payload.get("eval_set_id"), str) and payload["eval_set_id"], path.name
        assert isinstance(payload.get("eval_cases"), list), path.name
        assert len(payload["eval_cases"]) == 1, path.name

        case = payload["eval_cases"][0]
        assert isinstance(case.get("eval_id"), str) and case["eval_id"], path.name
        assert isinstance(case.get("conversation"), list) and case["conversation"], path.name


def test_all_eval_directories_include_test_config() -> None:
    for dirname in ("tools", "subagents", "root"):
        path = AGENTS_DIR / "evals" / "adk" / dirname / "test_config.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "criteria" in payload


def test_case_ids_are_unique_across_eval_assets() -> None:
    eval_files = sorted((AGENTS_DIR / "evals" / "adk").rglob("*.test.json"))
    case_ids: list[str] = []
    for path in eval_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        case_ids.extend(case["eval_id"] for case in payload["eval_cases"])

    assert len(case_ids) == len(set(case_ids))


def test_live_harness_registry_mentions_all_eval_assets() -> None:
    helpers_path = AGENTS_DIR / "evals" / "tests_adk" / "helpers.py"
    helpers_source = helpers_path.read_text(encoding="utf-8")
    referenced_paths = set(re.findall(r'rel_path="([^"]+)"', helpers_source))

    actual_paths = {
        str(path.relative_to(AGENTS_DIR / "evals")).replace("\\", "/")
        for path in (AGENTS_DIR / "evals" / "adk").rglob("*.test.json")
    }

    assert referenced_paths == actual_paths
