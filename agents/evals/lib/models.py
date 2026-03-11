from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

TierTarget = Literal["agent_only", "backend_e2e"]
EvalSuite = Literal[
    "direct_lookup",
    "historical",
    "predictive",
    "guardrails",
    "scorecard",
    "session",
]
SessionAction = Literal["new", "continue", "force_overflow_fixture"]


class JudgeThresholds(BaseModel):
    final_response_match_v2: float = 0.8
    rubric_based_final_response_quality_v1: float = 0.8
    tool_trajectory_avg_score: float = 0.7
    rubric_based_tool_use_quality_v1: float = 0.7
    hallucinations_v1: float = 0.85
    safety_v1: float = 1.0


class TurnExpectation(BaseModel):
    reference_response: str | None = None
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    expected_response_mode: str = "text"
    requires_risk_card: bool = False
    requires_artifact: bool = False


class ConversationTurnSpec(BaseModel):
    user_message: str
    session_action: SessionAction = "continue"
    fixture_name: str | None = None
    expectation: TurnExpectation = Field(default_factory=TurnExpectation)

    @field_validator("fixture_name")
    @classmethod
    def validate_fixture_name(
        cls, value: str | None, info: Any
    ) -> str | None:
        if info.data.get("session_action") == "force_overflow_fixture" and not value:
            raise ValueError("fixture_name is required when session_action is force_overflow_fixture")
        return value


class CaseOutcome(BaseModel):
    expected_domains: list[str] = Field(default_factory=list)
    expected_citations_contains: list[str] = Field(default_factory=list)
    expected_freshness_keys: list[str] = Field(default_factory=lambda: ["note"])
    expected_follow_up_prompt: str | None = None
    allowed_error_codes: list[str] = Field(default_factory=list)


class BackendAssertions(BaseModel):
    expect_json_schema_valid: bool = True
    expect_no_live_claim: bool = True
    expect_history_persisted: bool = False
    expect_same_public_session_id: bool = False
    expect_retry_session_suffix_used: bool = False


class AdkEvalSpec(BaseModel):
    criteria_profile: Literal["default", "guardrail", "session"] = "default"
    thresholds: JudgeThresholds = Field(default_factory=JudgeThresholds)


class MetroSenseEvalCase(BaseModel):
    case_id: str
    suite: EvalSuite
    tier_targets: list[TierTarget]
    conversation: list[ConversationTurnSpec]
    expected: CaseOutcome = Field(default_factory=CaseOutcome)
    adk_eval: AdkEvalSpec = Field(default_factory=AdkEvalSpec)
    backend_assertions: BackendAssertions = Field(default_factory=BackendAssertions)
    tags: list[str] = Field(default_factory=list)

    @field_validator("conversation")
    @classmethod
    def validate_conversation(cls, value: list[ConversationTurnSpec]) -> list[ConversationTurnSpec]:
        if not value:
            raise ValueError("conversation must contain at least one turn")
        if value[0].session_action == "continue":
            value[0].session_action = "new"
        return value


class DefaultSessionInput(BaseModel):
    app_name: str = "metrosense_agent"
    user_id: str = "metrosense-eval-user"
    state: dict[str, Any] = Field(default_factory=dict)


class MetroSenseEvalCatalog(BaseModel):
    catalog_id: str
    name: str
    description: str
    default_session_input: DefaultSessionInput = Field(default_factory=DefaultSessionInput)
    cases: list[MetroSenseEvalCase]


def schema_output_path(repo_root: Path) -> Path:
    return repo_root / "agents" / "evals" / "schema" / "metrosense_eval_catalog.schema.json"
