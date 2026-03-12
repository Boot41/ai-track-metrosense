from __future__ import annotations

import os
import socket
import threading
import time
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.db.models  # noqa: F401 — register all models
from app.api.deps import db_session as db_session_dep
from app.api.router import root_router
from app.core.config import get_settings
from app.db.base import Base
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from tests.integration.agent_stub import app as agent_stub_app

AGENT_HOST = "127.0.0.1"
AGENT_PORT = 18020


def _create_test_app() -> FastAPI:
    """Create a FastAPI app without lifespan (no shared engine)."""
    test_app = FastAPI(title="Test")
    test_app.add_middleware(RequestLoggingMiddleware)
    test_app.add_middleware(ErrorHandlerMiddleware)
    test_app.include_router(root_router)
    return test_app


@pytest.fixture(scope="session", autouse=True)
def agent_server() -> Generator[None, None, None]:
    os.environ["AGENT_SERVER_URL"] = f"http://{AGENT_HOST}:{AGENT_PORT}"
    os.environ["AGENT_INTERNAL_TOKEN"] = "test-internal-token"
    os.environ["JWT_SECRET"] = "test-secret-at-least-32-bytes-long"
    get_settings.cache_clear()

    config = uvicorn.Config(agent_stub_app, host=AGENT_HOST, port=AGENT_PORT, log_level="warning")
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((AGENT_HOST, AGENT_PORT)) == 0:
                break
        time.sleep(0.1)

    yield
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
async def engine() -> AsyncGenerator[Any, None]:
    settings = get_settings()
    eng = create_async_engine(settings.effective_db_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session_factory(engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def db(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    test_app = _create_test_app()

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    test_app.dependency_overrides[db_session_dep] = _override
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
