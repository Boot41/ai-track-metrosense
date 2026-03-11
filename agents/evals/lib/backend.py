from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .models import MetroSenseEvalCase


@dataclass
class TurnRunResult:
    user_message: str
    request_session_id: str
    response_status: int
    response_payload: dict[str, Any]


@dataclass
class CaseRunResult:
    case_id: str
    mode: str
    session_id: str | None = None
    turns: list[TurnRunResult] = field(default_factory=list)
    transcript_payload: dict[str, Any] | None = None
    fixture_payload: dict[str, Any] | None = None


async def ensure_logged_in(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    email: str,
    password: str,
) -> None:
    signup = await client.post(
        f"{base_url}/api/auth/signup",
        json={"email": email, "password": password},
    )
    if signup.status_code == 201:
        return
    if signup.status_code == 409:
        login = await client.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": password},
        )
        login.raise_for_status()
        return
    signup.raise_for_status()


def _fixture_path(repo_root: Path, fixture_name: str) -> Path:
    return repo_root / "agents" / "evals" / "fixtures" / fixture_name


def _new_session_id(case_id: str) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"eval-{case_id[:48]}-{suffix}"


async def run_backend_case(
    client: httpx.AsyncClient,
    *,
    repo_root: Path,
    base_url: str,
    case: MetroSenseEvalCase,
) -> CaseRunResult:
    session_id: str | None = None
    result = CaseRunResult(case_id=case.case_id, mode="live")

    for turn in case.conversation:
        if turn.session_action == "force_overflow_fixture":
            fixture_payload = _fixture_path(repo_root, turn.fixture_name or "").read_text(
                encoding="utf-8"
            )
            result.mode = "fixture"
            result.fixture_payload = httpx.Response(200, text=fixture_payload).json()
            return result

        if turn.session_action == "new" or session_id is None:
            session_id = _new_session_id(case.case_id)

        response = await client.post(
            f"{base_url}/api/chat",
            json={"session_id": session_id, "message": turn.user_message},
        )
        payload = response.json()
        result.turns.append(
            TurnRunResult(
                user_message=turn.user_message,
                request_session_id=session_id,
                response_status=response.status_code,
                response_payload=payload,
            )
        )

    result.session_id = session_id
    if session_id:
        transcript = await client.get(f"{base_url}/api/chat/sessions/{session_id}")
        if transcript.status_code == 200:
            result.transcript_payload = transcript.json()
    return result
