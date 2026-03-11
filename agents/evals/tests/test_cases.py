from __future__ import annotations

from pathlib import Path
import sys

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.catalog import load_catalog


def test_core_catalog_has_twenty_cases() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog(repo_root / "agents" / "evals" / "cases" / "core_v1.json")
    assert catalog.catalog_id == "core_v1"
    assert len(catalog.cases) == 20


def test_session_catalog_has_overflow_fixture_case() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    catalog = load_catalog(repo_root / "agents" / "evals" / "cases" / "session_v1.json")
    overflow_case = next(case for case in catalog.cases if case.case_id == "token_overflow_retry_001")
    assert overflow_case.conversation[0].session_action == "force_overflow_fixture"
    assert overflow_case.conversation[0].fixture_name == "backend_overflow_retry_fixture.json"
