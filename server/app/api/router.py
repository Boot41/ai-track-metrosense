from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health

root_router = APIRouter()
root_router.include_router(health.router)
