import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import settings
from app.core.config import Settings
from app.services import agent_proxy

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class CompositeHealthResponse(BaseModel):
    backend: str
    agent: str
    status: str


@router.get("/api/health", response_model=CompositeHealthResponse)
async def api_health(app_settings: Settings = Depends(settings)) -> CompositeHealthResponse:
    try:
        payload = await agent_proxy.get_agent_health(app_settings)
    except (httpx.HTTPError, ValueError):
        payload = {"backend": "ok", "agent": "down", "status": "degraded"}

    return CompositeHealthResponse.model_validate(payload)
