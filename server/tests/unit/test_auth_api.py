from __future__ import annotations

from collections.abc import Generator

import pytest
from httpx import AsyncClient

from app.api.deps import require_user
from app.core.config import get_settings
from app.db.models import User
from app.main import app
from app.services import auth_service


@pytest.fixture
def auth_override() -> Generator[None, None, None]:
    app.dependency_overrides[require_user] = lambda: User(
        id=1,
        email="test@example.com",
        password_hash="x",
    )
    yield
    app.dependency_overrides.pop(require_user, None)


@pytest.mark.asyncio
async def test_signup_sets_cookie(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _create_user(*_: object, **__: object) -> User:
        return User(id=1, email="test@example.com", password_hash="x")

    monkeypatch.setattr(auth_service, "create_user", _create_user)

    response = await client.post(
        "/api/auth/signup",
        json={"email": "test@example.com", "password": "password123"},
    )

    assert response.status_code == 201
    assert response.json() == {"user": {"id": 1, "email": "test@example.com"}}
    settings = get_settings()
    assert settings.auth_cookie_name in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_login_sets_cookie(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _authenticate_user(*_: object, **__: object) -> User | None:
        return User(id=2, email="login@example.com", password_hash="x")

    monkeypatch.setattr(auth_service, "authenticate_user", _authenticate_user)

    response = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json() == {"user": {"id": 2, "email": "login@example.com"}}
    settings = get_settings()
    assert settings.auth_cookie_name in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _authenticate_user(*_: object, **__: object) -> User | None:
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", _authenticate_user)

    response = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "badpass"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(client: AsyncClient, auth_override: None) -> None:
    response = await client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "email": "test@example.com"}


@pytest.mark.asyncio
async def test_logout_clears_cookie(client: AsyncClient, auth_override: None) -> None:
    response = await client.post("/api/auth/logout")
    assert response.status_code == 204
    settings = get_settings()
    assert settings.auth_cookie_name in response.headers.get("set-cookie", "")
