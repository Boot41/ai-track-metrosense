from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationHistory, Session


@pytest.mark.asyncio
async def test_chat_persists_session_and_turn_history(
    client: AsyncClient, db: AsyncSession
) -> None:
    email = "persist@example.com"
    password = "password123"
    session_id = "persist-session"

    signup = await client.post("/api/auth/signup", json={"email": email, "password": password})
    assert signup.status_code == 201

    first_chat = await client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "hello first turn"},
    )
    assert first_chat.status_code == 200

    second_chat = await client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "hello second turn"},
    )
    assert second_chat.status_code == 200

    persisted_session = (
        await db.execute(select(Session).where(Session.session_id == session_id))
    ).scalar_one()
    assert persisted_session.total_turns == 2
    assert persisted_session.active_flag is True

    row_count = (
        await db.execute(
            select(func.count())
            .select_from(
                ConversationHistory,
            )
            .where(ConversationHistory.session_id == session_id)
        )
    ).scalar_one()
    assert row_count == 4

    rows = (
        (
            await db.execute(
                select(ConversationHistory)
                .where(ConversationHistory.session_id == session_id)
                .order_by(ConversationHistory.timestamp.asc())
            )
        )
        .scalars()
        .all()
    )

    user_rows = [row for row in rows if row.role == "user"]
    assistant_rows = [row for row in rows if row.role == "assistant"]

    assert len(user_rows) == 2
    assert len(assistant_rows) == 2
    assert {row.message for row in user_rows} == {"hello first turn", "hello second turn"}
    assert all(row.message == "Stubbed response from agent." for row in assistant_rows)
    assert all(row.latency_ms is not None for row in assistant_rows)
