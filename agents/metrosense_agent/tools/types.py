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
    dataset_note: str | None
    available_from: str | None
    available_to: str | None
    last_updated_at: str | None
    record_count_returned: int | None
    resolved_location: dict[str, Any] | None


class ToolResult(TypedDict):
    data: Any
    meta: ToolMeta


def success_result(
    data: Any,
    source: Literal["backend", "filesystem"],
    dataset_note: str | None = None,
    available_from: str | None = None,
    available_to: str | None = None,
    last_updated_at: str | None = None,
    record_count_returned: int | None = None,
    resolved_location: dict[str, Any] | None = None,
) -> ToolResult:
    return {
        "data": data,
        "meta": {
            "ok": True,
            "source": source,
            "error_code": None,
            "error_detail": None,
            "dataset_note": dataset_note,
            "available_from": available_from,
            "available_to": available_to,
            "last_updated_at": last_updated_at,
            "record_count_returned": record_count_returned,
            "resolved_location": resolved_location,
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
            "available_from": None,
            "available_to": None,
            "last_updated_at": None,
            "record_count_returned": None,
            "resolved_location": None,
        },
    }
