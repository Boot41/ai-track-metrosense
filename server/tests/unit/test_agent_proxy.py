from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

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


class _OverflowThenSuccessClient:
    def __init__(self, *_: object, **__: object) -> None:
        self._call_count = 0

    async def __aenter__(self) -> _OverflowThenSuccessClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(self, url: str, *_: object, **kwargs: object) -> _FakeResponse:
        self._call_count += 1
        if self._call_count in {1, 3}:
            return _FakeResponse(status_code=201)
        if self._call_count == 2:
            payload = {
                "error": {
                    "code": 400,
                    "message": (
                        "The input token count exceeds the maximum number of tokens "
                        "allowed (1048576)."
                    ),
                    "status": "INVALID_ARGUMENT",
                }
            }
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", url),
                response=httpx.Response(400, json=payload, request=httpx.Request("POST", url)),
            )
        assert self._call_count == 4
        body = kwargs.get("json")
        assert isinstance(body, dict)
        assert isinstance(body.get("sessionId"), str)
        assert "--retry-" in body["sessionId"]
        return _FakeResponse(
            json_payload=[
                {"content": {"role": "model", "parts": [{"text": "Reply after overflow reset"}]}}
            ]
        )


@pytest.mark.asyncio
async def test_get_chat_response_persists_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    db_session.add = MagicMock()
    upsert = AsyncMock()
    append = AsyncMock(return_value="turn-id")

    monkeypatch.setattr(agent_proxy.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(
        agent_proxy.conversation_service, "session_owner_id", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        agent_proxy.conversation_service, "derive_session_title", lambda _: "Hello title"
    )
    monkeypatch.setattr(agent_proxy.conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(agent_proxy.conversation_service, "append_turn", append)

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-1",
        message="hello",
    )

    assert payload["message"] == "Persisted assistant reply"
    assert payload["response_text"] == "Persisted assistant reply"
    assert payload["session_id"] == "s-1"
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
    db_session.add = MagicMock()
    upsert = AsyncMock()
    append = AsyncMock(side_effect=RuntimeError("db write failure"))

    monkeypatch.setattr(agent_proxy.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(
        agent_proxy.conversation_service, "session_owner_id", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        agent_proxy.conversation_service, "derive_session_title", lambda _: "Hello title"
    )
    monkeypatch.setattr(agent_proxy.conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(agent_proxy.conversation_service, "append_turn", append)

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-2",
        message="hello",
    )

    assert payload["message"] == "Persisted assistant reply"
    assert payload["response_text"] == "Persisted assistant reply"
    assert payload["session_id"] == "s-2"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.rollback.assert_awaited_once()
    db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_chat_response_retries_once_on_input_token_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    db_session.add = MagicMock()
    upsert = AsyncMock()
    append = AsyncMock(return_value="turn-id")

    monkeypatch.setattr(agent_proxy.httpx, "AsyncClient", _OverflowThenSuccessClient)
    monkeypatch.setattr(
        agent_proxy.conversation_service, "session_owner_id", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        agent_proxy.conversation_service, "derive_session_title", lambda _: "Hello title"
    )
    monkeypatch.setattr(agent_proxy.conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(agent_proxy.conversation_service, "append_turn", append)

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-overflow",
        message="hello",
    )

    assert payload["message"] == "Reply after overflow reset"
    assert payload["response_text"] == "Reply after overflow reset"
    assert payload["session_id"] == "s-overflow"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.commit.assert_awaited_once()
    db_session.rollback.assert_not_awaited()
