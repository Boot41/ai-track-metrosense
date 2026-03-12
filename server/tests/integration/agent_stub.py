from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Agent Stub")


class RunRequest(BaseModel):
    appName: str
    userId: str
    sessionId: str
    newMessage: dict[str, object] | None = None
    streaming: bool = False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"agent": "ok"}


@app.post("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def create_session(
    app_name: str,
    user_id: str,
    session_id: str,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> dict[str, str]:
    _require_token(x_internal_token)
    return {"status": "ok"}


@app.post("/run")
async def run_agent(
    _: RunRequest,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> list[dict[str, object]]:
    _require_token(x_internal_token)
    return [
        {
            "content": {
                "role": "model",
                "parts": [{"text": "Stubbed response from agent."}],
            }
        }
    ]


def _require_token(header_value: str | None) -> None:
    internal_token = os.getenv("AGENT_INTERNAL_TOKEN", "").strip()
    if not internal_token:
        raise RuntimeError("AGENT_INTERNAL_TOKEN must be set for agent stub")
    if header_value != internal_token:
        raise HTTPException(status_code=401, detail="Invalid internal token")
