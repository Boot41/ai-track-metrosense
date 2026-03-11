from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_user
from app.api.routes import auth, chat, health, internal

root_router = APIRouter()
root_router.include_router(health.router)
root_router.include_router(auth.router)
root_router.include_router(internal.router)

protected_router = APIRouter(dependencies=[Depends(require_user)])
protected_router.include_router(chat.router)
root_router.include_router(protected_router)
