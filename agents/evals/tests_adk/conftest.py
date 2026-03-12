from __future__ import annotations

import sys
from pathlib import Path

import dotenv
import pytest

pytest_plugins = ("pytest_asyncio",)

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / "agents"

if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))


@pytest.fixture(scope="session", autouse=True)
def load_env() -> None:
    dotenv.load_dotenv()
