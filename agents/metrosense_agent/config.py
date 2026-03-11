from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()  # loads agents/.env when running via `adk api_server`


@dataclass(frozen=True)
class AgentSettings:
    model: str
    backend_internal_url: str
    agent_internal_token: str
    documents_path: str


@lru_cache
def get_settings() -> AgentSettings:
    model = os.getenv("AGENT_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    backend_internal_url = os.getenv("BACKEND_INTERNAL_URL", "").strip()
    agent_internal_token = os.getenv("AGENT_INTERNAL_TOKEN", "").strip()
    documents_path = os.getenv("DOCUMENTS_PATH", "").strip()

    return AgentSettings(
        model=model,
        backend_internal_url=backend_internal_url,
        agent_internal_token=agent_internal_token,
        documents_path=documents_path,
    )
