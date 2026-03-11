from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationHistory
from app.db.models import Session as DBSession


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def upsert_session(
    session: AsyncSession,
    session_id: str,
    user_role: str = "user",
) -> None:
    now = _utcnow()
    statement = insert(DBSession).values(
        session_id=session_id,
        user_role=user_role,
        created_at=now,
        last_active_at=now,
        total_turns=1,
        active_flag=True,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DBSession.session_id],
        set_={
            "last_active_at": now,
            "total_turns": DBSession.total_turns + 1,
            "active_flag": True,
        },
    )
    await session.execute(statement)


async def append_turn(
    session: AsyncSession,
    session_id: str,
    user_message: str,
    assistant_message: str,
    agents_invoked: list[str],
    latency_ms: int | None = None,
) -> str:
    now = _utcnow()
    user_turn_id = str(uuid4())
    assistant_turn_id = str(uuid4())
    payload = [
        ConversationHistory(
            turn_id=user_turn_id,
            session_id=session_id,
            role="user",
            message=user_message,
            agents_invoked=agents_invoked,
            response_mode=None,
            cited_documents=[],
            cited_records=[],
            timestamp=now,
            latency_ms=None,
        ),
        ConversationHistory(
            turn_id=assistant_turn_id,
            session_id=session_id,
            role="assistant",
            message=assistant_message,
            agents_invoked=agents_invoked,
            response_mode=None,
            cited_documents=[],
            cited_records=[],
            timestamp=now,
            latency_ms=latency_ms,
        ),
    ]
    session.add_all(payload)
    return assistant_turn_id
