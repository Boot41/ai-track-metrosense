from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationHistory
from app.db.models import Session as DBSession


def _utcnow() -> datetime:
    return datetime.now(UTC)


def derive_session_title(message: str, max_length: int = 80) -> str:
    normalized = " ".join(message.strip().split())
    if not normalized:
        return "Untitled Chat"
    return normalized[:max_length]


async def session_owner_id(session: AsyncSession, session_id: str) -> int | None:
    stmt = select(DBSession.user_id).where(DBSession.session_id == session_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert_session(
    session: AsyncSession,
    session_id: str,
    user_id: int,
    title: str,
    user_role: str = "user",
) -> None:
    now = _utcnow()
    statement = insert(DBSession).values(
        session_id=session_id,
        user_id=user_id,
        user_role=user_role,
        title=title,
        created_at=now,
        last_active_at=now,
        total_turns=1,
        active_flag=True,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DBSession.session_id],
        set_={
            "user_id": func.coalesce(DBSession.user_id, user_id),
            "last_active_at": now,
            "total_turns": DBSession.total_turns + 1,
            "active_flag": True,
            "title": func.coalesce(DBSession.title, title),
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
    # Flush so downstream rows (for example audit_log) can safely FK the assistant turn.
    await session.flush()
    return assistant_turn_id


async def list_sessions(
    session: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[DBSession]:
    stmt = (
        select(DBSession)
        .where(DBSession.user_id == user_id)
        .order_by(DBSession.last_active_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def list_session_messages(
    session: AsyncSession,
    user_id: int,
    session_id: str,
) -> tuple[DBSession | None, list[ConversationHistory]]:
    session_stmt = select(DBSession).where(
        DBSession.session_id == session_id, DBSession.user_id == user_id
    )
    owned_session = (await session.execute(session_stmt)).scalar_one_or_none()
    if owned_session is None:
        return None, []

    history_stmt = (
        select(ConversationHistory)
        .where(ConversationHistory.session_id == session_id)
        .order_by(ConversationHistory.timestamp.asc())
    )
    messages = list((await session.execute(history_stmt)).scalars().all())
    return owned_session, messages
