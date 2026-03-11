from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _documents_path() -> Path | None:
    raw_path = os.getenv("DOCUMENTS_PATH", "").strip()
    if not raw_path:
        return None
    return Path(raw_path)


def _load_indexes(base_path: Path) -> list[dict[str, Any]]:
    index_files = sorted(base_path.glob("*_index.json"))
    indexes: list[dict[str, Any]] = []

    for path in index_files:
        try:
            indexes.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return []

    return indexes


def _contains_thresholds(index_doc: dict[str, Any]) -> bool:
    toc = index_doc.get("table_of_contents", [])
    if not isinstance(toc, list):
        return False
    return any(
        bool(section.get("contains_thresholds"))
        for section in toc
        if isinstance(section, dict)
    )


async def list_document_indexes(
    document_type: str | None = None,
    ward_name: str | None = None,
    contains_thresholds: bool | None = None,
) -> list[dict[str, Any]]:
    base_path = _documents_path()
    if base_path is None or not base_path.exists() or not base_path.is_dir():
        return []

    indexes = _load_indexes(base_path)

    filtered: list[dict[str, Any]] = []
    ward_lookup = (ward_name or "").strip().lower()
    requested_type = (document_type or "").strip().lower()

    for idx in indexes:
        if (
            requested_type
            and str(idx.get("document_type", "")).lower() != requested_type
        ):
            continue

        if ward_lookup:
            wards = idx.get("wards_covered", [])
            if not isinstance(wards, list):
                continue
            if ward_lookup not in {str(ward).strip().lower() for ward in wards}:
                continue

        if (
            contains_thresholds is not None
            and _contains_thresholds(idx) != contains_thresholds
        ):
            continue

        filtered.append(idx)

    return filtered


async def fetch_document_section(
    document_id: str, section_id: str
) -> dict[str, Any] | None:
    base_path = _documents_path()
    if base_path is None or not base_path.exists() or not base_path.is_dir():
        return None

    indexes = _load_indexes(base_path)

    document: dict[str, Any] | None = None
    section: dict[str, Any] | None = None

    for idx in indexes:
        if str(idx.get("document_id")) != document_id:
            continue

        toc = idx.get("table_of_contents", [])
        if not isinstance(toc, list):
            continue

        for item in toc:
            if isinstance(item, dict) and str(item.get("section_id")) == section_id:
                document = idx
                section = item
                break
        if section is not None:
            break

    if document is None or section is None:
        return None

    text_file = section.get("text_file")
    if not text_file:
        return None

    section_path = base_path / str(text_file)

    try:
        content = section_path.read_text(encoding="utf-8")
    except OSError:
        return None

    return {
        "document_id": document_id,
        "section_id": section_id,
        "title": section.get("title"),
        "summary": section.get("summary"),
        "page_start": section.get("page_start"),
        "page_end": section.get("page_end"),
        "text_file": str(text_file),
        "content": content,
    }
