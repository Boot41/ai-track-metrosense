from __future__ import annotations

from typing import Any, Literal, TypedDict

ErrorCode = Literal[
    "BACKEND_TIMEOUT",
    "BACKEND_HTTP_ERROR",
    "BACKEND_UNAUTHORIZED",
    "BACKEND_CONFIG_MISSING",
    "DOCUMENTS_PATH_MISSING",
    "INDEX_PARSE_ERROR",
    "SECTION_NOT_FOUND",
    "FILE_READ_ERROR",
]


class ToolMeta(TypedDict):
    ok: bool
    source: Literal["backend", "filesystem"]
    error_code: ErrorCode | None
    error_detail: str | None
    # Always present on successful backend responses.
    # Format: "MetroSense 2023 dataset. Most recent record: <observed_at>."
    # Agents MUST copy this verbatim into data_freshness and prefix responses
    # with it so users know the data is historical, not live.
    dataset_note: str | None


class ToolResult(TypedDict):
    data: Any
    meta: ToolMeta


def success_result(
    data: Any,
    source: Literal["backend", "filesystem"],
    dataset_note: str | None = None,
) -> ToolResult:
    return {
        "data": data,
        "meta": {
            "ok": True,
            "source": source,
            "error_code": None,
            "error_detail": None,
            "dataset_note": dataset_note,
        },
    }


def failure_result(
    source: Literal["backend", "filesystem"],
    error_code: ErrorCode,
    error_detail: str,
    fallback_data: Any,
) -> ToolResult:
    return {
        "data": fallback_data,
        "meta": {
            "ok": False,
            "source": source,
            "error_code": error_code,
            "error_detail": error_detail,
            "dataset_note": None,
        },
    }
