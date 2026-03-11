from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, require_user, settings
from app.core.config import Settings
from app.core.security import create_access_token
from app.db.models import User
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthPayload(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr


class AuthResponse(BaseModel):
    user: UserResponse


def _set_auth_cookie(response: Response, token: str, app_settings: Settings) -> None:
    response.set_cookie(
        key=app_settings.auth_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=app_settings.env == "production",
        max_age=app_settings.jwt_expires_minutes * 60,
        path="/",
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: AuthPayload,
    response: Response,
    session: AsyncSession = Depends(db_session),
    app_settings: Settings = Depends(settings),
) -> AuthResponse:
    if len(payload.password) < app_settings.password_min_length:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password too short")

    try:
        user = await auth_service.create_user(session, payload.email, payload.password)
    except ValueError as exc:
        if str(exc) == "EMAIL_IN_USE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already in use"
            ) from exc
        raise

    token = create_access_token(subject=str(user.id), settings=app_settings)
    _set_auth_cookie(response, token, app_settings)
    return AuthResponse(user=UserResponse(id=user.id, email=user.email))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: AuthPayload,
    response: Response,
    session: AsyncSession = Depends(db_session),
    app_settings: Settings = Depends(settings),
) -> AuthResponse:
    user = await auth_service.authenticate_user(session, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=str(user.id), settings=app_settings)
    _set_auth_cookie(response, token, app_settings)
    return AuthResponse(user=UserResponse(id=user.id, email=user.email))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    app_settings: Settings = Depends(settings),
    _: User = Depends(require_user),
) -> None:
    response.delete_cookie(key=app_settings.auth_cookie_name, path="/")
    return None


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(require_user)) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)
