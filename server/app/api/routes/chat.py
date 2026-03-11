from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.api.deps import db_session, require_user, settings
from app.core.config import Settings
from app.db.models import User
from app.services import agent_proxy, conversation_service

router = APIRouter(prefix="/api", tags=["chat"])


class ArtifactPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    title: str
    source: str | None = None
    columns: list[str] | None = None
    rows: list[list[object]] | None = None
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


class BarricadeRecommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    underpass_name: str
    reason: str


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
    rainfall_expected_mm_per_hr: float | None = None
    rainfall_classification: str | None = None
    barricade_recommendations: list[BarricadeRecommendation] | None = None


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


class ChatSessionSummary(BaseModel):
    session_id: str
    title: str
    last_active_at: str
    total_turns: int


class ChatSessionsResponse(BaseModel):
    sessions: list[ChatSessionSummary]


class ChatTranscriptMessage(BaseModel):
    role: str
    message: str
    timestamp: str


class ChatTranscriptResponse(BaseModel):
    session_id: str
    title: str
    last_active_at: str
    messages: list[ChatTranscriptMessage]


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
    current_user: User = Depends(require_user),
) -> ChatResponse | JSONResponse:
    try:
        response_payload = await agent_proxy.get_chat_response(
            settings=app_settings,
            db_session=session,
            user_id=current_user.id,
            session_id=payload.session_id,
            message=payload.message,
        )
    except PermissionError:
        return _error_response(
            code="CHAT_SESSION_NOT_FOUND",
            message="Chat session was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
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


@router.get("/chat/sessions", response_model=ChatSessionsResponse)
async def list_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(require_user),
) -> ChatSessionsResponse:
    sessions = await conversation_service.list_sessions(
        session=session,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return ChatSessionsResponse(
        sessions=[
            ChatSessionSummary(
                session_id=item.session_id,
                title=item.title or "Untitled Chat",
                last_active_at=item.last_active_at.isoformat(),
                total_turns=item.total_turns,
            )
            for item in sessions
        ]
    )


@router.get("/chat/sessions/{session_id}", response_model=ChatTranscriptResponse)
async def get_chat_session(
    session_id: str,
    session: AsyncSession = Depends(db_session),
    current_user: User = Depends(require_user),
) -> ChatTranscriptResponse:
    owned_session, messages = await conversation_service.list_session_messages(
        session=session,
        user_id=current_user.id,
        session_id=session_id,
    )
    if owned_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return ChatTranscriptResponse(
        session_id=owned_session.session_id,
        title=owned_session.title or "Untitled Chat",
        last_active_at=owned_session.last_active_at.isoformat(),
        messages=[
            ChatTranscriptMessage(
                role=msg.role,
                message=msg.message,
                timestamp=msg.timestamp.isoformat(),
            )
            for msg in messages
        ],
    )


@router.delete("/chat/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_session(
    session_id: str,  # noqa: ARG001 - placeholder until agents service supports reset
    app_settings: Settings = Depends(settings),  # noqa: ARG001
) -> None:
    return None
