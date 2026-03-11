from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.api.deps import db_session, settings
from app.core.config import Settings
from app.services import agent_proxy

router = APIRouter(prefix="/api", tags=["chat"])


class ArtifactPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    title: str
    source: str
    description: str | None = None


class RiskMetric(BaseModel):
    model_config = ConfigDict(extra="ignore")

    probability: float | None = None
    severity: str | None = None
    congestion_score: float | None = None


class HealthAdvisory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    aqi: int | None = None
    aqi_category: str | None = None


class EmergencyReadiness(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recommendation: str
    actions: list[str] | None = None


class RiskCardPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    neighborhood: str
    generated_at: str
    overall_risk_score: float
    flood_risk: RiskMetric | None = None
    power_outage_risk: RiskMetric | None = None
    traffic_delay_index: RiskMetric | None = None
    health_advisory: HealthAdvisory | None = None
    emergency_readiness: EmergencyReadiness | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response_mode: str = "text"
    response_text: str
    citations_summary: list[dict[str, object]] = Field(default_factory=list)
    data_freshness_summary: dict[str, object] = Field(default_factory=dict)
    risk_card: RiskCardPayload | None = None
    artifact: ArtifactPayload | None = None
    follow_up_prompt: str | None = None
    message: str  # Backward-compatible alias of response_text


class ErrorPayload(BaseModel):
    code: str
    message: str




def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": ErrorPayload(code=code, message=message).model_dump()},
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        502: {"description": "Agent unavailable"},
        504: {"description": "Agent timeout"},
    },
)
async def chat(
    payload: ChatRequest,
    app_settings: Settings = Depends(settings),
    session: AsyncSession = Depends(db_session),
) -> ChatResponse | JSONResponse:
    try:
        response_payload = await agent_proxy.get_chat_response(
            settings=app_settings,
            db_session=session,
            session_id=payload.session_id,
            message=payload.message,
        )
    except httpx.TimeoutException:
        return _error_response(
            code="AGENT_TIMEOUT",
            message="The agent service did not respond in time.",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except (httpx.HTTPError, ValueError):
        return _error_response(
            code="AGENT_UNAVAILABLE",
            message="The agent service is currently unavailable.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    return ChatResponse.model_validate(response_payload)


@router.delete("/chat/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_session(
    session_id: str,  # noqa: ARG001 - placeholder until agents service supports reset
    app_settings: Settings = Depends(settings),  # noqa: ARG001
) -> None:
    return None
