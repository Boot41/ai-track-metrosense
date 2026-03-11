from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .catalog import dump_json
from .models import MetroSenseEvalCatalog, MetroSenseEvalCase


def _content(role: str, text: str) -> dict[str, Any]:
    return {"role": role, "parts": [{"text": text}]}


def _tool_use(name: str) -> dict[str, Any]:
    return {"name": name, "args": {}}


def _invocation(case_id: str, turn_index: int, case: MetroSenseEvalCase) -> dict[str, Any]:
    turn = case.conversation[turn_index]
    expectation = turn.expectation
    return {
        "invocation_id": f"{case_id}-turn-{turn_index + 1}",
        "user_content": _content("user", turn.user_message),
        "final_response": (
            _content("model", expectation.reference_response)
            if expectation.reference_response
            else None
        ),
        "intermediate_data": {
            "tool_uses": [_tool_use(tool_name) for tool_name in expectation.expected_tools],
            "tool_responses": [],
            "intermediate_responses": [],
        },
        "creation_timestamp": time.time(),
    }


def build_eval_set(catalog: MetroSenseEvalCatalog, *, tier_target: str = "agent_only") -> dict[str, Any]:
    eval_cases: list[dict[str, Any]] = []
    for case in catalog.cases:
        if tier_target not in case.tier_targets:
            continue
        eval_cases.append(
            {
                "eval_id": case.case_id,
                "conversation": [
                    _invocation(case.case_id, turn_index, case)
                    for turn_index in range(len(case.conversation))
                ],
                "session_input": catalog.default_session_input.model_dump(),
                "creation_timestamp": time.time(),
            }
        )

    return {
        "eval_set_id": catalog.catalog_id,
        "name": catalog.name,
        "description": catalog.description,
        "eval_cases": eval_cases,
        "creation_timestamp": time.time(),
    }


def _rubrics_from_markdown(path: Path, rubric_type: str) -> list[dict[str, Any]]:
    rubrics: list[dict[str, Any]] = []
    index = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        index += 1
        text = stripped[2:].strip()
        rubrics.append(
            {
                "rubric_id": f"{rubric_type.lower()}_{index}",
                "rubric_content": {"text_property": text},
                "type": rubric_type,
            }
        )
    return rubrics


def build_eval_config(repo_root: Path, catalog: MetroSenseEvalCatalog) -> dict[str, Any]:
    del catalog
    rubrics_dir = repo_root / "agents" / "evals" / "rubrics"
    final_response_rubrics = _rubrics_from_markdown(
        rubrics_dir / "final_response_quality.md",
        "FINAL_RESPONSE_QUALITY",
    )
    tool_use_rubrics = _rubrics_from_markdown(
        rubrics_dir / "tool_use_quality.md",
        "TOOL_USE_QUALITY",
    )

    return {
        "criteria": {
            "tool_trajectory_avg_score": {"threshold": 0.7, "matchType": "IN_ORDER"},
            "final_response_match_v2": {
                "threshold": 0.75,
                "judgeModelOptions": {"judgeModel": "gemini-2.5-flash", "numSamples": 3},
            },
            "rubric_based_final_response_quality_v1": {
                "threshold": 0.75,
                "judgeModelOptions": {"judgeModel": "gemini-2.5-flash", "numSamples": 3},
                "rubrics": final_response_rubrics,
            },
            "rubric_based_tool_use_quality_v1": {
                "threshold": 0.7,
                "judgeModelOptions": {"judgeModel": "gemini-2.5-flash", "numSamples": 3},
                "rubrics": tool_use_rubrics,
            },
            "hallucinations_v1": {
                "threshold": 0.85,
                "judgeModelOptions": {"judgeModel": "gemini-2.5-flash", "numSamples": 3},
                "evaluateIntermediateNlResponses": True,
            },
            "safety_v1": {
                "threshold": 1.0,
                "judgeModelOptions": {"judgeModel": "gemini-2.5-flash", "numSamples": 3},
            },
        }
    }


def write_generated_files(repo_root: Path, catalog: MetroSenseEvalCatalog) -> tuple[Path, Path]:
    generated_dir = repo_root / "agents" / "evals" / "adk" / "generated"
    eval_set_path = generated_dir / f"{catalog.catalog_id}.evalset.json"
    eval_config_path = generated_dir / f"{catalog.catalog_id}.evalconfig.json"
    dump_json(eval_set_path, build_eval_set(catalog))
    dump_json(eval_config_path, build_eval_config(repo_root, catalog))
    return eval_set_path, eval_config_path
