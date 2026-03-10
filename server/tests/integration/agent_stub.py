from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Agent Stub")


class RunRequest(BaseModel):
    appName: str
    userId: str
    sessionId: str
    newMessage: dict | None = None
    streaming: bool = False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"agent": "ok"}


@app.post("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def create_session(app_name: str, user_id: str, session_id: str) -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
async def run_agent(_: RunRequest) -> list[dict]:
    return [
        {
            "content": {
                "role": "model",
                "parts": [{"text": "Stubbed response from agent."}],
            }
        }
    ]
