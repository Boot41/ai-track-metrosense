from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import Settings
from app.services import agent_proxy


@pytest.mark.asyncio
async def test_agent_proxy_requires_internal_token() -> None:
    settings = Settings(agent_internal_token="")
    with pytest.raises(ValueError, match="AGENT_INTERNAL_TOKEN"):
        await agent_proxy.get_agent_health(settings)


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_payload: Any = None,
        should_raise: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_payload = json_payload
        self._should_raise = should_raise

    def json(self) -> Any:
        return self._json_payload

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "http://test/run"),
                response=httpx.Response(500),
            )


class _FakeAsyncClient:
    def __init__(self, *_: object, **__: object) -> None:
        self._call_count = 0

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(self, *_: object, **__: object) -> _FakeResponse:
        self._call_count += 1
        if self._call_count == 1:
            return _FakeResponse(status_code=201)
        return _FakeResponse(
            json_payload=[
                {"content": {"role": "model", "parts": [{"text": "Persisted assistant reply"}]}}
            ]
        )


@pytest.mark.asyncio
async def test_get_chat_response_persists_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    upsert = AsyncMock()
    append = AsyncMock(return_value="turn-id")

    monkeypatch.setattr(agent_proxy.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(agent_proxy.conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(agent_proxy.conversation_service, "append_turn", append)

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        session_id="s-1",
        message="hello",
    )

    assert payload["message"] == "Persisted assistant reply"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.commit.assert_awaited_once()
    db_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_chat_response_returns_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    upsert = AsyncMock()
    append = AsyncMock(side_effect=RuntimeError("db write failure"))

    monkeypatch.setattr(agent_proxy.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(agent_proxy.conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(agent_proxy.conversation_service, "append_turn", append)

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        session_id="s-2",
        message="hello",
    )

    assert payload["message"] == "Persisted assistant reply"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.rollback.assert_awaited_once()
    db_session.commit.assert_not_awaited()
