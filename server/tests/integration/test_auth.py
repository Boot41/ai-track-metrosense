from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


@pytest.mark.asyncio
async def test_auth_chat_logout_flow(client: AsyncClient, db: AsyncSession) -> None:
    email = "integration@example.com"
    password = "password123"

    signup = await client.post("/api/auth/signup", json={"email": email, "password": password})
    assert signup.status_code == 201

    result = await db.execute(select(User).where(User.email == email))
    assert result.scalar_one_or_none() is not None

    chat = await client.post("/api/chat", json={"session_id": "integration", "message": "hello"})
    assert chat.status_code == 200
    assert chat.json()["message"] == "Stubbed response from agent."

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204

    chat_after_logout = await client.post(
        "/api/chat", json={"session_id": "integration", "message": "hello again"}
    )
    assert chat_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient) -> None:
    email = "loginflow@example.com"
    password = "password123"

    await client.post("/api/auth/signup", json={"email": email, "password": password})
    login = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    assert login.json()["user"]["email"] == email
