from __future__ import annotations

import os
from typing import Any

import httpx

from .types import ToolResult, failure_result, success_result


def _backend_base_url() -> str | None:
    base_url = os.getenv("BACKEND_INTERNAL_URL", "").strip()
    if not base_url:
        return None
    return base_url.rstrip("/")


def _internal_token() -> str | None:
    token = os.getenv("AGENT_INTERNAL_TOKEN", "").strip()
    if not token:
        return None
    return token


async def backend_get(path: str, params: dict[str, Any] | None = None) -> ToolResult:
    base_url = _backend_base_url()
    token = _internal_token()
    if not base_url or not token:
        return failure_result(
            source="backend",
            error_code="BACKEND_CONFIG_MISSING",
            error_detail=(
                "BACKEND_INTERNAL_URL and AGENT_INTERNAL_TOKEN must be set for backend tools"
            ),
            fallback_data=[],
        )

    headers = {"X-Internal-Token": token}
    url = f"{base_url}{path}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=headers)
    except httpx.TimeoutException as exc:
        return failure_result(
            source="backend",
            error_code="BACKEND_TIMEOUT",
            error_detail=str(exc),
            fallback_data=[],
        )
    except httpx.HTTPError as exc:
        return failure_result(
            source="backend",
            error_code="BACKEND_HTTP_ERROR",
            error_detail=str(exc),
            fallback_data=[],
        )

    if response.status_code == httpx.codes.UNAUTHORIZED:
        return failure_result(
            source="backend",
            error_code="BACKEND_UNAUTHORIZED",
            error_detail=response.text,
            fallback_data=[],
        )

    if response.is_error:
        return failure_result(
            source="backend",
            error_code="BACKEND_HTTP_ERROR",
            error_detail=f"{response.status_code}: {response.text}",
            fallback_data=[],
        )

    try:
        payload = response.json()
    except ValueError as exc:
        return failure_result(
            source="backend",
            error_code="BACKEND_HTTP_ERROR",
            error_detail=f"Invalid JSON response: {exc}",
            fallback_data=[],
        )

    if isinstance(payload, dict) and "data" in payload and "meta" in payload:
        meta = payload.get("meta")
        if isinstance(meta, dict):
            return success_result(
                payload.get("data"),
                source="backend",
                dataset_note=meta.get("dataset_note"),
                available_from=meta.get("available_from"),
                available_to=meta.get("available_to"),
                last_updated_at=meta.get("last_updated_at"),
                record_count_returned=meta.get("record_count_returned"),
                resolved_location=meta.get("resolved_location"),
            )

    return success_result(payload, source="backend")
