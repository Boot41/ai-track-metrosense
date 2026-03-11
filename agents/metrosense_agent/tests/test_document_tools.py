from __future__ import annotations

from pathlib import Path

import pytest

from metrosense_agent.tools.shared.document_tools import (
    fetch_document_section,
    list_document_indexes,
)


@pytest.mark.asyncio
async def test_list_document_indexes_missing_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DOCUMENTS_PATH", raising=False)
    result = await list_document_indexes()
    assert result == []


@pytest.mark.asyncio
async def test_list_document_indexes_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    docs_path = Path(__file__).resolve().parents[3] / "server" / "Documents_Metrosense"
    monkeypatch.setenv("DOCUMENTS_PATH", str(docs_path))

    result = await list_document_indexes(
        document_type="drainage_plan", ward_name="Bellandur"
    )
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_fetch_document_section_success(monkeypatch: pytest.MonkeyPatch) -> None:
    docs_path = Path(__file__).resolve().parents[3] / "server" / "Documents_Metrosense"
    monkeypatch.setenv("DOCUMENTS_PATH", str(docs_path))

    result = await fetch_document_section("drainage_plan_bbmp_2019", "s2")
    assert result is not None
    assert result["document_id"] == "drainage_plan_bbmp_2019"
    assert "content" in result
