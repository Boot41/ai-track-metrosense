from __future__ import annotations

from datetime import date, datetime
from typing import Any

_PRIMARY_TIME_FIELDS = (
    "observed_at",
    "reported_at",
    "started_at",
    "updated_at",
    "created_at",
)
_SECONDARY_TIME_FIELDS = (
    "resolved_at",
    "restored_at",
)
_MONTH_FIELDS = ("month",)


def _normalise_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _normalise_rows(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _collect_values(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for row in rows:
        for key in keys:
            normalised = _normalise_scalar(row.get(key))
            if normalised is not None:
                values.append(normalised)
    return values


def _coverage_bounds(rows: list[dict[str, Any]]) -> tuple[str | None, str | None, str | None]:
    primary_values = _collect_values(rows, _PRIMARY_TIME_FIELDS)
    if primary_values:
        return min(primary_values), max(primary_values), max(primary_values)

    secondary_values = _collect_values(rows, _SECONDARY_TIME_FIELDS)
    if secondary_values:
        return min(secondary_values), max(secondary_values), max(secondary_values)

    month_values = _collect_values(rows, _MONTH_FIELDS)
    if month_values:
        return min(month_values), max(month_values), max(month_values)

    return None, None, None


def _record_count(data: Any) -> int:
    if data is None:
        return 0
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        return 1
    return 0


def build_dataset_note(
    *,
    domain: str,
    available_from: str | None,
    available_to: str | None,
    last_updated_at: str | None,
    record_count_returned: int,
    resolved_location: dict[str, Any] | None = None,
) -> str:
    scope = domain.replace("_", " ")
    if resolved_location:
        location_parts = [
            f"{key}={value}"
            for key, value in resolved_location.items()
            if value is not None and value != ""
        ]
        if location_parts:
            scope = f"{scope} ({', '.join(location_parts)})"

    if record_count_returned == 0:
        return f"No records returned for {scope}."

    coverage = "coverage unavailable"
    if available_from and available_to:
        coverage = f"coverage in result: {available_from} to {available_to}"
    elif available_to:
        coverage = f"latest available in result: {available_to}"

    latest = f" Latest record: {last_updated_at}." if last_updated_at else ""
    return f"{scope.title()} — {coverage}. Records returned: {record_count_returned}.{latest}"


def build_internal_response(
    *,
    domain: str,
    data: Any,
    resolved_location: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = _normalise_rows(data)
    available_from, available_to, last_updated_at = _coverage_bounds(rows)
    record_count_returned = _record_count(data)
    return {
        "data": data,
        "meta": {
            "ok": True,
            "domain": domain,
            "dataset_note": build_dataset_note(
                domain=domain,
                available_from=available_from,
                available_to=available_to,
                last_updated_at=last_updated_at,
                record_count_returned=record_count_returned,
                resolved_location=resolved_location,
            ),
            "available_from": available_from,
            "available_to": available_to,
            "last_updated_at": last_updated_at,
            "record_count_returned": record_count_returned,
            "resolved_location": resolved_location,
        },
    }
