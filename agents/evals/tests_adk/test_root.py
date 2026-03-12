from __future__ import annotations

import pytest

from .helpers import iter_targets, run_eval_target

TARGETS = iter_targets("root")
pytestmark = pytest.mark.skipif(not TARGETS, reason="No root evals selected.")


@pytest.mark.asyncio
@pytest.mark.parametrize("target", TARGETS, ids=lambda item: item.case_id)
async def test_root(target) -> None:
    await run_eval_target(target)
