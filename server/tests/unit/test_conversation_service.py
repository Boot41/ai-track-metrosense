from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import conversation_service


@pytest.mark.asyncio
async def test_upsert_session_executes_statement() -> None:
    session = AsyncMock()

    await conversation_service.upsert_session(
        session,
        session_id="s-1",
        user_id=1,
        title="Test title",
        user_role="user",
    )

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_append_turn_adds_user_and_assistant_rows() -> None:
    session = AsyncMock()
    session.add_all = MagicMock()

    assistant_turn_id = await conversation_service.append_turn(
        session=cast(Any, session),
        session_id="s-1",
        user_message="hello",
        assistant_message="world",
        agents_invoked=[],
        latency_ms=42,
    )

    assert assistant_turn_id
    session.add_all.assert_called_once()
    payload = session.add_all.call_args.args[0]
    assert len(payload) == 2
    assert payload[0].role == "user"
    assert payload[1].role == "assistant"
    assert payload[1].latency_ms == 42
