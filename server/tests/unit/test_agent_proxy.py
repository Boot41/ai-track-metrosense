from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services import agent_proxy


@pytest.mark.asyncio
async def test_agent_proxy_requires_internal_token() -> None:
    settings = Settings(agent_internal_token="")
    with pytest.raises(ValueError, match="AGENT_INTERNAL_TOKEN"):
        await agent_proxy.get_agent_health(settings)
