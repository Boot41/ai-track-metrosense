from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from google.adk.evaluation.agent_evaluator import AgentEvaluator

REPO_ROOT = Path(__file__).resolve().parents[3]
EVALS_DIR = REPO_ROOT / "agents" / "evals"


@dataclass(frozen=True)
class EvalTarget:
    case_id: str
    layer: str
    rel_path: str
    agent_name: str | None = None

    @property
    def abs_path(self) -> Path:
        return EVALS_DIR / self.rel_path


REGISTRY: tuple[EvalTarget, ...] = (
    EvalTarget(
        case_id="resolve_location_bellandur",
        layer="tools",
        rel_path="adk/tools/resolve_location_bellandur.test.json",
        agent_name="chat_agent",
    ),
    EvalTarget(
        case_id="list_document_indexes_thresholds",
        layer="tools",
        rel_path="adk/tools/list_document_indexes_thresholds.test.json",
        agent_name="chat_agent",
    ),
    EvalTarget(
        case_id="fetch_document_section_drainage_plan_s2",
        layer="tools",
        rel_path="adk/tools/fetch_document_section_drainage_plan_s2.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_weather_current_bellandur",
        layer="tools",
        rel_path="adk/tools/get_weather_current_bellandur.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_weather_historical_bellandur",
        layer="tools",
        rel_path="adk/tools/get_weather_historical_bellandur.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_weather_summary_bellandur_2025",
        layer="tools",
        rel_path="adk/tools/get_weather_summary_bellandur_2025.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_weather_extremes_hottest_day_2025",
        layer="tools",
        rel_path="adk/tools/get_weather_extremes_hottest_day_2025.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_lake_hydrology_bellandur",
        layer="tools",
        rel_path="adk/tools/get_lake_hydrology_bellandur.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_flood_incidents_bellandur",
        layer="tools",
        rel_path="adk/tools/get_flood_incidents_bellandur.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="get_aqi_current_koramangala",
        layer="tools",
        rel_path="adk/tools/get_aqi_current_koramangala.test.json",
        agent_name="heat_health_agent",
    ),
    EvalTarget(
        case_id="get_aqi_historical_bellandur_last_week",
        layer="tools",
        rel_path="adk/tools/get_aqi_historical_bellandur_last_week.test.json",
        agent_name="heat_health_agent",
    ),
    EvalTarget(
        case_id="get_aqi_summary_bellandur_2025",
        layer="tools",
        rel_path="adk/tools/get_aqi_summary_bellandur_2025.test.json",
        agent_name="heat_health_agent",
    ),
    EvalTarget(
        case_id="get_ward_profile_hebbal",
        layer="tools",
        rel_path="adk/tools/get_ward_profile_hebbal.test.json",
        agent_name="heat_health_agent",
    ),
    EvalTarget(
        case_id="get_power_outage_events_hebbal",
        layer="tools",
        rel_path="adk/tools/get_power_outage_events_hebbal.test.json",
        agent_name="infrastructure_agent",
    ),
    EvalTarget(
        case_id="get_traffic_current_bellandur",
        layer="tools",
        rel_path="adk/tools/get_traffic_current_bellandur.test.json",
        agent_name="logistics_agent",
    ),
    EvalTarget(
        case_id="get_traffic_corridor_orr",
        layer="tools",
        rel_path="adk/tools/get_traffic_corridor_orr.test.json",
        agent_name="logistics_agent",
    ),
    EvalTarget(
        case_id="chat_agent_aqi_delegation",
        layer="subagents",
        rel_path="adk/subagents/chat_agent_aqi_delegation.test.json",
        agent_name="chat_agent",
    ),
    EvalTarget(
        case_id="flood_vulnerability_agent_underpass_barricade",
        layer="subagents",
        rel_path="adk/subagents/flood_vulnerability_agent_underpass_barricade.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="flood_vulnerability_agent_future_data_gap",
        layer="subagents",
        rel_path="adk/subagents/flood_vulnerability_agent_future_data_gap.test.json",
        agent_name="flood_vulnerability_agent",
    ),
    EvalTarget(
        case_id="heat_health_agent_weekly_aqi",
        layer="subagents",
        rel_path="adk/subagents/heat_health_agent_weekly_aqi.test.json",
        agent_name="heat_health_agent",
    ),
    EvalTarget(
        case_id="heat_health_agent_future_data_gap",
        layer="subagents",
        rel_path="adk/subagents/heat_health_agent_future_data_gap.test.json",
        agent_name="heat_health_agent",
    ),
    EvalTarget(
        case_id="infrastructure_agent_treefall_risk",
        layer="subagents",
        rel_path="adk/subagents/infrastructure_agent_treefall_risk.test.json",
        agent_name="infrastructure_agent",
    ),
    EvalTarget(
        case_id="infrastructure_agent_latest_resolved_outage",
        layer="subagents",
        rel_path="adk/subagents/infrastructure_agent_latest_resolved_outage.test.json",
        agent_name="infrastructure_agent",
    ),
    EvalTarget(
        case_id="logistics_agent_orr_delay_factor",
        layer="subagents",
        rel_path="adk/subagents/logistics_agent_orr_delay_factor.test.json",
        agent_name="logistics_agent",
    ),
    EvalTarget(
        case_id="logistics_agent_sarjapur_waterlogging_history",
        layer="subagents",
        rel_path="adk/subagents/logistics_agent_sarjapur_waterlogging_history.test.json",
        agent_name="logistics_agent",
    ),
    EvalTarget(
        case_id="root_agent_greeting_only",
        layer="root",
        rel_path="adk/root/root_agent_greeting_only.test.json",
    ),
    EvalTarget(
        case_id="root_agent_greeting_with_question",
        layer="root",
        rel_path="adk/root/root_agent_greeting_with_question.test.json",
    ),
    EvalTarget(
        case_id="root_agent_bellandur_flood_risk",
        layer="root",
        rel_path="adk/root/root_agent_bellandur_flood_risk.test.json",
    ),
    EvalTarget(
        case_id="root_agent_off_domain_refusal",
        layer="root",
        rel_path="adk/root/root_agent_off_domain_refusal.test.json",
    ),
    EvalTarget(
        case_id="root_agent_location_not_found",
        layer="root",
        rel_path="adk/root/root_agent_location_not_found.test.json",
    ),
    EvalTarget(
        case_id="root_agent_prompt_injection_refusal",
        layer="root",
        rel_path="adk/root/root_agent_prompt_injection_refusal.test.json",
    ),
    EvalTarget(
        case_id="root_agent_flood_to_traffic_conversation",
        layer="root",
        rel_path="adk/root/root_agent_flood_to_traffic_conversation.test.json",
    ),
)


def _filter_value() -> str:
    return os.getenv("METROSENSE_EVAL_FILE", "").strip().replace("\\", "/")


def iter_targets(layer: str) -> tuple[EvalTarget, ...]:
    requested = _filter_value()
    candidates = tuple(target for target in REGISTRY if target.layer == layer)
    if not requested:
        return candidates

    return tuple(
        target
        for target in candidates
        if requested in {target.case_id, target.rel_path, Path(target.rel_path).name}
    )


def eval_num_runs() -> int:
    raw = os.getenv("METROSENSE_EVAL_NUM_RUNS", "1").strip()
    try:
        value = int(raw)
    except ValueError:
        return 1
    return max(value, 1)


async def run_eval_target(target: EvalTarget) -> None:
    os.environ.setdefault(
        "DOCUMENTS_PATH", str(REPO_ROOT / "server" / "Documents_Metrosense")
    )
    await AgentEvaluator.evaluate(
        "metrosense_agent",
        str(target.abs_path),
        num_runs=eval_num_runs(),
        agent_name=target.agent_name,
        print_detailed_results=True,
    )
