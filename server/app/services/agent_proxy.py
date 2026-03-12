from __future__ import annotations

import ast
import json
import re
import time
from typing import Any
from uuid import uuid4

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import AuditLog
from app.services import conversation_service
from app.services.runtime_context import build_runtime_context

CHAT_TIMEOUT_SECONDS = 600.0


def _auth_headers(settings: Settings) -> dict[str, str]:
    token = settings.agent_internal_token.strip()
    if not token:
        raise ValueError("AGENT_INTERNAL_TOKEN must be set for agent requests")
    return {"X-Internal-Token": token}


def _is_input_token_limit_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None or response.status_code != 400:
        return False
    body = response.text.lower()
    return "input token count exceeds the maximum number of tokens allowed" in body


def _overflow_retry_session_id(session_id: str) -> str:
    # Keep the id compact and deterministic enough for log correlation.
    compact_base = session_id[:96]
    return f"{compact_base}--retry-{int(time.time() * 1000)}"


def _extract_message_from_events(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        content = event.get("content")
        if not isinstance(content, dict):
            continue
        role = content.get("role")
        if role not in (None, "model"):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        texts = [
            t
            for part in parts
            if isinstance(part, dict) and isinstance((t := part.get("text")), str)
        ]
        if texts:
            return "\n".join(texts)
    raise ValueError("Agent response did not include model text")


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.DOTALL)
_LEGACY_SECTION_RE = re.compile(r"\b(summary|details|health_advisory)\s*:", re.IGNORECASE)


def _normalise_freshness(value: Any) -> dict[str, Any]:
    """Ensure data_freshness_summary is always a dict for Pydantic validation."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        return {"note": value}
    return {}


def _normalise_citations(value: Any) -> list[dict[str, Any]]:
    """Ensure citations_summary is always a list of objects for Pydantic validation."""
    if not isinstance(value, list):
        return []

    normalised: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            normalised.append(item)
        elif isinstance(item, str) and item.strip():
            normalised.append({"source": item})
    return normalised


def _normalise_severity(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().upper()


def _normalise_risk_metric(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    probability = value.get("probability")
    score = value.get("score")
    congestion_score = value.get("congestion_score")

    normalised: dict[str, Any] = {
        "probability": probability if isinstance(probability, int | float) else None,
        "severity": _normalise_severity(value.get("severity") or value.get("label")),
        "congestion_score": congestion_score if isinstance(congestion_score, int | float) else None,
    }

    if normalised["probability"] is None and isinstance(score, int | float):
        normalised["probability"] = max(0.0, min(1.0, float(score) / 10.0))

    if normalised["congestion_score"] is None and isinstance(score, int | float):
        normalised["congestion_score"] = float(score)

    if all(item is None for item in normalised.values()):
        return None
    return normalised


def _normalise_health_advisory(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    advisory = {
        "aqi": value.get("aqi") if isinstance(value.get("aqi"), int) else None,
        "aqi_category": value.get("aqi_category")
        if isinstance(value.get("aqi_category"), str)
        else None,
    }
    if advisory["aqi"] is None and advisory["aqi_category"] is None:
        return None
    return advisory


def _normalise_emergency_readiness(value: Any, advisory: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        if isinstance(advisory, str) and advisory.strip():
            return {"recommendation": advisory.strip(), "actions": None}
        return None

    recommendation = value.get("recommendation")
    if not isinstance(recommendation, str) or not recommendation.strip():
        if isinstance(value.get("detail"), str) and value["detail"].strip():
            recommendation = value["detail"].strip()
        elif isinstance(advisory, str) and advisory.strip():
            recommendation = advisory.strip()
        elif isinstance(value.get("label"), str) and value["label"].strip():
            recommendation = value["label"].strip()
        else:
            return None

    actions = value.get("actions")
    if not isinstance(actions, list):
        actions = None
    else:
        actions = [item for item in actions if isinstance(item, str) and item.strip()]

    return {"recommendation": recommendation, "actions": actions or None}


def _compute_overall_risk_score(card: dict[str, Any]) -> float:
    raw_score = card.get("overall_risk_score")
    if isinstance(raw_score, int | float):
        return float(raw_score)

    component_scores: list[float] = []
    for key in ("flood_risk", "power_outage_risk", "traffic_delay_index"):
        metric = card.get(key)
        if isinstance(metric, dict):
            score = metric.get("congestion_score")
            if key != "traffic_delay_index":
                probability = metric.get("probability")
                if isinstance(probability, int | float):
                    score = float(probability) * 10.0
            if isinstance(score, int | float):
                component_scores.append(float(score))

    readiness = card.get("emergency_readiness")
    if isinstance(readiness, dict):
        readiness_score = readiness.get("score")
        if isinstance(readiness_score, int | float):
            component_scores.append(max(0.0, 10.0 - float(readiness_score)))

    if not component_scores:
        return 0.0
    return round(sum(component_scores) / len(component_scores), 1)


def _normalise_risk_card(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    flood_risk = _normalise_risk_metric(value.get("flood_risk"))
    power_outage_risk = _normalise_risk_metric(
        value.get("power_outage_risk") or value.get("outage_risk")
    )
    traffic_delay_index = _normalise_risk_metric(value.get("traffic_delay_index"))
    health_advisory = _normalise_health_advisory(value.get("health_advisory"))
    emergency_readiness = _normalise_emergency_readiness(
        value.get("emergency_readiness"),
        value.get("advisory"),
    )

    rainfall_expected = value.get("rainfall_expected_mm_per_hr")
    if not isinstance(rainfall_expected, int | float):
        rainfall_expected = None

    rainfall_classification = value.get("rainfall_classification")
    if not isinstance(rainfall_classification, str):
        rainfall_classification = None

    barricades = value.get("barricade_recommendations")
    if isinstance(barricades, list):
        barricades = [
            item
            for item in barricades
            if isinstance(item, dict)
            and isinstance(item.get("underpass_name"), str)
            and isinstance(item.get("reason"), str)
        ]
    else:
        barricades = None

    overall_risk_score = _compute_overall_risk_score(
        {
            **value,
            "flood_risk": flood_risk,
            "power_outage_risk": power_outage_risk,
            "traffic_delay_index": traffic_delay_index,
        }
    )

    card = {
        "neighborhood": value.get("neighborhood") or value.get("location") or "Unknown",
        "generated_at": value.get("generated_at") or value.get("as_of") or "",
        "overall_risk_score": overall_risk_score,
        "flood_risk": flood_risk,
        "power_outage_risk": power_outage_risk,
        "traffic_delay_index": traffic_delay_index,
        "health_advisory": health_advisory,
        "emergency_readiness": emergency_readiness,
        "rainfall_expected_mm_per_hr": (
            float(rainfall_expected) if rainfall_expected is not None else None
        ),
        "rainfall_classification": rainfall_classification,
        "barricade_recommendations": barricades or None,
    }
    return card


def _strip_fences(text: str) -> str:
    """Return the content inside the first markdown code fence, or the original text."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _prettify_metric_name(key: str) -> str:
    if " " in key or "(" in key or ")" in key:
        return key.strip()
    return key.replace("_", " ").strip().title()


def _format_table_value(value: Any) -> str | int | float | None:
    if isinstance(value, int | float | str) or value is None:
        return value
    return str(value)


def _build_table_artifact_from_month_blocks(
    month_blocks: list[dict[str, Any]], title: str
) -> dict[str, Any] | None:
    if len(month_blocks) < 2:
        return None

    columns = ["Metric"] + [
        str(block.get("month", f"Period {index + 1}")) for index, block in enumerate(month_blocks)
    ]
    metric_keys: list[str] = []
    for block in month_blocks:
        for key in block.keys():
            if key in {"location", "month"} or key in metric_keys:
                continue
            metric_keys.append(key)

    rows: list[list[Any]] = []
    for metric_key in metric_keys:
        row: list[Any] = [_prettify_metric_name(metric_key)]
        for block in month_blocks:
            row.append(_format_table_value(block.get(metric_key)))
        rows.append(row)

    return {
        "type": "table",
        "title": title,
        "columns": columns,
        "rows": rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_row_dicts(
    rows_data: list[dict[str, Any]], title: str
) -> dict[str, Any] | None:
    if len(rows_data) < 2:
        return None

    row_label_key = next(
        (key for key in ("Month", "month", "Location", "location") if key in rows_data[0]),
        None,
    )
    if row_label_key is None:
        return None

    columns = ["Metric"] + [
        str(row.get(row_label_key, f"Period {index + 1}")) for index, row in enumerate(rows_data)
    ]
    metric_keys: list[str] = []
    for row_data in rows_data:
        for key in row_data.keys():
            if key == row_label_key or key in metric_keys:
                continue
            metric_keys.append(key)

    rows: list[list[Any]] = []
    for metric_key in metric_keys:
        row: list[Any] = [_prettify_metric_name(metric_key)]
        for row_data in rows_data:
            row.append(_format_table_value(row_data.get(metric_key)))
        rows.append(row)

    return {
        "type": "table",
        "title": title,
        "columns": columns,
        "rows": rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_columnar_dict(
    table_data: dict[str, Any], title: str
) -> dict[str, Any] | None:
    metric_column = table_data.get("Metric")
    if not isinstance(metric_column, list) or len(metric_column) == 0:
        return None

    period_columns = [
        key
        for key, value in table_data.items()
        if key != "Metric" and isinstance(key, str) and isinstance(value, list)
    ]
    if len(period_columns) < 2:
        return None

    rows: list[list[Any]] = []
    for index, metric in enumerate(metric_column):
        row: list[Any] = [_format_table_value(metric)]
        for period in period_columns:
            values = table_data[period]
            assert isinstance(values, list)
            row.append(_format_table_value(values[index] if index < len(values) else None))
        rows.append(row)

    return {
        "type": "table",
        "title": title,
        "columns": ["Metric", *period_columns],
        "rows": rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_month_column_dict(
    table_data: dict[str, Any], title: str
) -> dict[str, Any] | None:
    month_column = table_data.get("Month")
    if not isinstance(month_column, list) or len(month_column) < 2:
        return None

    metric_keys = [
        key
        for key, value in table_data.items()
        if key != "Month" and isinstance(key, str) and isinstance(value, list)
    ]
    if not metric_keys:
        return None

    rows: list[list[Any]] = []
    for metric_key in metric_keys:
        values = table_data[metric_key]
        assert isinstance(values, list)
        row: list[Any] = [_prettify_metric_name(metric_key)]
        for index in range(len(month_column)):
            row.append(_format_table_value(values[index] if index < len(values) else None))
        rows.append(row)

    return {
        "type": "table",
        "title": title,
        "columns": ["Metric", *[_format_table_value(item) for item in month_column]],
        "rows": rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_headers_rows_dict(
    table_data: dict[str, Any], title: str
) -> dict[str, Any] | None:
    headers = table_data.get("headers")
    rows = table_data.get("rows")
    if (
        not isinstance(headers, list)
        or len(headers) < 3
        or not all(isinstance(item, str) for item in headers)
    ):
        return None
    if not isinstance(rows, list) or not rows:
        return None
    if not all(isinstance(row, list) for row in rows):
        return None

    normalised_rows = [[_format_table_value(cell) for cell in row] for row in rows]
    return {
        "type": "table",
        "title": title,
        "columns": headers,
        "rows": normalised_rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_metric_rows(
    rows_data: list[dict[str, Any]], title: str
) -> dict[str, Any] | None:
    if len(rows_data) < 2:
        return None
    if not all(isinstance(row.get("Metric"), str) for row in rows_data):
        return None

    period_columns: list[str] = []
    for row_data in rows_data:
        for key in row_data.keys():
            if key == "Metric" or key in period_columns:
                continue
            period_columns.append(key)

    if len(period_columns) < 2:
        return None

    rows: list[list[Any]] = []
    for row_data in rows_data:
        row: list[Any] = [_format_table_value(row_data.get("Metric"))]
        for period in period_columns:
            row.append(_format_table_value(row_data.get(period)))
        rows.append(row)

    return {
        "type": "table",
        "title": title,
        "columns": ["Metric", *period_columns],
        "rows": rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_period_dicts(
    table_data: dict[str, Any], title: str
) -> dict[str, Any] | None:
    periods = [
        key for key, value in table_data.items() if isinstance(key, str) and isinstance(value, dict)
    ]
    if len(periods) < 2:
        return None

    metric_keys: list[str] = []
    for period in periods:
        values = table_data[period]
        assert isinstance(values, dict)
        for key, value in values.items():
            if isinstance(value, dict | list):
                return None
            if key not in metric_keys:
                metric_keys.append(key)

    rows: list[list[Any]] = []
    for metric_key in metric_keys:
        row: list[Any] = [_prettify_metric_name(metric_key)]
        for period in periods:
            values = table_data[period]
            assert isinstance(values, dict)
            row.append(_format_table_value(values.get(metric_key)))
        rows.append(row)

    return {
        "type": "table",
        "title": title,
        "columns": ["Metric", *periods],
        "rows": rows,
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def _build_table_artifact_from_details(
    details: dict[str, Any], title: str
) -> dict[str, Any] | None:
    comparison_table = details.get("comparison_table")
    if isinstance(comparison_table, list) and comparison_table:
        artifact = _build_table_artifact_from_metric_rows(
            [item for item in comparison_table if isinstance(item, dict)],
            title=title,
        )
        if artifact is not None:
            return artifact
        artifact = _build_table_artifact_from_month_blocks(
            [item for item in comparison_table if isinstance(item, dict) and "month" in item],
            title=title,
        )
        if artifact is not None:
            return artifact

    for detail_key, detail_value in details.items():
        if isinstance(detail_key, str) and isinstance(detail_value, list):
            artifact_title = (
                title if detail_key.strip().lower() in {"table", "rows"} else detail_key
            )
            artifact = _build_table_artifact_from_row_dicts(
                [item for item in detail_value if isinstance(item, dict)],
                title=artifact_title,
            )
            if artifact is not None:
                return artifact
        if isinstance(detail_key, str) and isinstance(detail_value, dict):
            artifact = _build_table_artifact_from_headers_rows_dict(
                detail_value,
                title=detail_key,
            )
            if artifact is not None:
                return artifact
            artifact = _build_table_artifact_from_month_column_dict(
                detail_value,
                title=detail_key,
            )
            if artifact is not None:
                return artifact
            artifact = _build_table_artifact_from_columnar_dict(
                detail_value,
                title=detail_key,
            )
            if artifact is not None:
                return artifact
            artifact = _build_table_artifact_from_period_dicts(
                detail_value,
                title=detail_key,
            )
            if artifact is not None:
                return artifact

    comparison = details.get("comparison")
    month_blocks = [
        value
        for key, value in details.items()
        if key != "comparison" and isinstance(value, dict) and "month" in value
    ]
    artifact = _build_table_artifact_from_month_blocks(month_blocks, title=title)
    if artifact is None:
        return None

    if isinstance(comparison, dict):
        rows = artifact["rows"]
        assert isinstance(rows, list)
        for key, value in comparison.items():
            row = [_prettify_metric_name(key), _format_table_value(value)]
            while len(row) < len(artifact["columns"]):
                row.append(None)
            rows.append(row)
    return artifact


def _build_table_artifact_from_top_level_comparison(
    parsed: dict[str, Any], title: str
) -> dict[str, Any] | None:
    comparison_table = parsed.get("comparison_table")
    if not isinstance(comparison_table, list):
        return None
    return _build_table_artifact_from_month_blocks(
        [item for item in comparison_table if isinstance(item, dict) and "month" in item],
        title=title,
    )


def _normalise_artifact(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    artifact_type = value.get("type")
    title = value.get("title")
    if not isinstance(artifact_type, str) or not isinstance(title, str):
        return None

    if artifact_type == "table":
        columns = value.get("columns")
        rows = value.get("rows")
        if not isinstance(columns, list) or not all(isinstance(item, str) for item in columns):
            return None
        if not isinstance(rows, list):
            return None
        normalised_rows: list[list[Any]] = []
        for row in rows:
            if not isinstance(row, list):
                return None
            normalised_rows.append([_format_table_value(item) for item in row])
        description = value.get("description")
        return {
            "type": "table",
            "title": title,
            "columns": columns,
            "rows": normalised_rows,
            "description": description if isinstance(description, str) else None,
            "source": None,
        }

    if artifact_type == "html":
        source = value.get("source")
        description = value.get("description")
        return {
            "type": "html",
            "title": title,
            "source": source if isinstance(source, str) else "",
            "description": description if isinstance(description, str) else None,
            "columns": None,
            "rows": None,
        }

    return None


def _extract_legacy_summary_sections(raw_text: str) -> tuple[str, str, str | None] | None:
    matches = list(_LEGACY_SECTION_RE.finditer(raw_text))
    if len(matches) < 2:
        return None

    summary_match = next((match for match in matches if match.group(1).lower() == "summary"), None)
    details_match = next((match for match in matches if match.group(1).lower() == "details"), None)
    if (
        summary_match is None
        or details_match is None
        or summary_match.start() >= details_match.start()
    ):
        return None

    health_match = next(
        (
            match
            for match in matches
            if match.group(1).lower() == "health_advisory" and match.start() > details_match.start()
        ),
        None,
    )

    summary = raw_text[summary_match.end() : details_match.start()].strip()
    summary = re.sub(r"(?:\s*\.)+\s*$", "", summary).strip()
    details_end = health_match.start() if health_match is not None else len(raw_text)
    details = raw_text[details_match.end() : details_end].strip()
    details = re.sub(r"\s*\.+\s*$", "", details).strip()

    health = None
    if health_match is not None:
        health = raw_text[health_match.end() :].strip()

    if not summary or not details:
        return None
    return summary, details, health or None


def _parse_legacy_summary_details(raw_text: str, session_id: str) -> dict[str, Any] | None:
    sections = _extract_legacy_summary_sections(raw_text)
    if sections is None:
        return None

    summary, details_text, health_advisory = sections

    try:
        details = ast.literal_eval(details_text)
    except (ValueError, SyntaxError):
        return None

    if not isinstance(details, dict):
        return None

    return _build_summary_details_payload(
        session_id=session_id,
        summary=summary,
        details=details,
        health_advisory=health_advisory,
    )


def _build_summary_details_payload(
    *,
    session_id: str,
    summary: str,
    details: dict[str, Any],
    health_advisory: Any = None,
    citations_summary: list[dict[str, Any]] | None = None,
    data_freshness_summary: dict[str, Any] | None = None,
    risk_card: dict[str, Any] | None = None,
    follow_up_prompt: Any = None,
) -> dict[str, Any] | None:
    artifact = _build_table_artifact_from_details(details, title="Weather Comparison")
    if artifact is None:
        return None

    response_text = summary
    if isinstance(health_advisory, str) and health_advisory.strip():
        response_text = f"{summary}\n\nHealth note: {health_advisory.strip()}"

    return {
        "session_id": session_id,
        "response_mode": "text",
        "response_text": response_text,
        "citations_summary": citations_summary or [],
        "data_freshness_summary": data_freshness_summary or {},
        "risk_card": risk_card,
        "artifact": artifact,
        "follow_up_prompt": follow_up_prompt,
        "message": response_text,
    }


def _augment_message_with_runtime_context(message: str, runtime_context: dict[str, Any]) -> str:
    return (
        "[MetroSense Runtime Context]\n"
        "This block is injected by the backend. Use it only for availability and freshness "
        "context. Tool outputs remain authoritative.\n"
        f"{json.dumps(runtime_context, separators=(',', ':'), ensure_ascii=True)}\n\n"
        "[User Message]\n"
        f"{message}"
    )


def _synthesize_from_level1(parsed: dict[str, Any]) -> str | None:
    """
    Try to build a human-readable response_text from a Level-1 agent payload
    (fields: agent, status, confidence, data, errors, citations, …).
    Returns None when nothing useful can be extracted.
    """
    errors: list[Any] = parsed.get("errors") or []
    status: str = str(parsed.get("status", ""))
    data = parsed.get("data")

    if errors:
        readable = "; ".join(str(e) for e in errors if e)
        if readable:
            return readable

    if isinstance(data, dict):
        parts = [f"{k}: {v}" for k, v in data.items() if v is not None]
        if parts:
            return ". ".join(parts)
    elif isinstance(data, list) and data:
        return str(data[0])

    agent_name: str = str(parsed.get("agent", "agent"))
    if status:
        return f"{agent_name} returned status: {status}"

    return None


def _parse_level2_payload(raw_text: str, session_id: str) -> dict[str, Any]:
    default_payload: dict[str, Any] = {
        "session_id": session_id,
        "response_mode": "text",
        "response_text": raw_text,
        "citations_summary": [],
        "data_freshness_summary": {},
        "risk_card": None,
        "artifact": None,
        "follow_up_prompt": None,
        # Backward-compatible field for existing callers.
        "message": raw_text,
    }

    # Strip markdown code fences that LLMs sometimes emit around JSON output.
    json_candidate = _strip_fences(raw_text)

    try:
        parsed = json.loads(json_candidate)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(json_candidate)
        except (ValueError, SyntaxError):
            legacy_payload = _parse_legacy_summary_details(raw_text, session_id)
            if legacy_payload is not None:
                return legacy_payload
            return default_payload

    if not isinstance(parsed, dict):
        return default_payload

    summary = parsed.get("summary")
    details = parsed.get("details")
    if isinstance(summary, str) and isinstance(details, str):
        try:
            details = ast.literal_eval(details)
        except (ValueError, SyntaxError):
            details = None

    if isinstance(summary, str) and isinstance(details, dict):
        summary_details_payload = _build_summary_details_payload(
            session_id=session_id,
            summary=summary,
            details=details,
            health_advisory=parsed.get("health_advisory"),
            citations_summary=_normalise_citations(parsed.get("citations_summary", [])),
            data_freshness_summary=_normalise_freshness(parsed.get("data_freshness_summary")),
            risk_card=_normalise_risk_card(parsed.get("risk_card")),
            follow_up_prompt=parsed.get("follow_up_prompt"),
        )
        if summary_details_payload is not None:
            return summary_details_payload

    top_level_artifact = _build_table_artifact_from_top_level_comparison(
        parsed,
        title=str(parsed.get("title", "Comparison Table")),
    )
    if top_level_artifact is not None:
        response_text = parsed.get("response_text")
        if not isinstance(response_text, str) or not response_text.strip():
            response_text = str(parsed.get("summary", "Comparison ready."))
        return {
            "session_id": session_id,
            "response_mode": parsed.get("response_mode", "text"),
            "response_text": response_text,
            "citations_summary": _normalise_citations(parsed.get("citations_summary", [])),
            "data_freshness_summary": _normalise_freshness(parsed.get("data_freshness_summary")),
            "risk_card": _normalise_risk_card(parsed.get("risk_card")),
            "artifact": top_level_artifact,
            "follow_up_prompt": parsed.get("follow_up_prompt"),
            "message": response_text,
        }

    # --- Level-2 shape: has response_text directly ---
    response_text = parsed.get("response_text")
    if isinstance(response_text, str) and response_text.strip():
        normalised_artifact = _normalise_artifact(parsed.get("artifact"))
        if normalised_artifact is None:
            embedded_legacy_payload = _parse_legacy_summary_details(response_text, session_id)
            if embedded_legacy_payload is not None:
                response_text = embedded_legacy_payload["response_text"]
                normalised_artifact = embedded_legacy_payload["artifact"]

        return {
            "session_id": session_id,
            "response_mode": parsed.get("response_mode", "text"),
            "response_text": response_text,
            "citations_summary": _normalise_citations(parsed.get("citations_summary", [])),
            "data_freshness_summary": _normalise_freshness(parsed.get("data_freshness_summary")),
            "risk_card": _normalise_risk_card(parsed.get("risk_card")),
            "artifact": normalised_artifact,
            "follow_up_prompt": parsed.get("follow_up_prompt"),
            "message": response_text,
        }

    # --- Level-1 shape: agent/status/data/errors/confidence ---
    level1_keys = {"agent", "status", "data", "errors", "confidence", "query_id"}
    if level1_keys & parsed.keys():
        data = parsed.get("data")
        if isinstance(data, dict):
            summary = data.get("summary")
            details = data.get("details")
            if isinstance(summary, str) and isinstance(details, dict):
                summary_details_payload = _build_summary_details_payload(
                    session_id=session_id,
                    summary=summary,
                    details=details,
                    health_advisory=data.get("health_advisory"),
                    citations_summary=_normalise_citations(parsed.get("citations", [])),
                    data_freshness_summary=_normalise_freshness(parsed.get("data_freshness")),
                )
                if summary_details_payload is not None:
                    return summary_details_payload
        synthesized = _synthesize_from_level1(parsed)
        if synthesized:
            return {
                "session_id": session_id,
                "response_mode": "text",
                "response_text": synthesized,
                "citations_summary": _normalise_citations(parsed.get("citations", [])),
                "data_freshness_summary": _normalise_freshness(parsed.get("data_freshness")),
                "risk_card": None,
                "artifact": None,
                "follow_up_prompt": None,
                "message": synthesized,
            }

    return default_payload


async def _ensure_session(
    client: httpx.AsyncClient,
    base_url: str,
    app_name: str,
    user_id: str,
    session_id: str,
    headers: dict[str, str],
) -> None:
    response = await client.post(
        f"{base_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}",
        headers=headers,
        json=None,
    )
    if response.status_code in {200, 201, 204, 409}:
        return
    response.raise_for_status()


async def _run_agent_once(
    client: httpx.AsyncClient,
    base_url: str,
    app_name: str,
    user_id: str,
    session_id: str,
    message: str,
    headers: dict[str, str],
) -> list[dict[str, Any]]:
    await _ensure_session(
        client=client,
        base_url=base_url,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        headers=headers,
    )
    response = await client.post(
        f"{base_url}/run",
        headers=headers,
        json={
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {"role": "user", "parts": [{"text": message}]},
            "streaming": False,
        },
    )
    response.raise_for_status()
    events = response.json()
    if not isinstance(events, list):
        raise ValueError("Agent response must be a list of events")
    return events


async def get_chat_response(
    settings: Settings,
    db_session: AsyncSession,
    user_id: int,
    session_id: str,
    message: str,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    owner_id = await conversation_service.session_owner_id(db_session, session_id=session_id)
    if owner_id is not None and owner_id != user_id:
        raise PermissionError("Session does not belong to current user")

    headers = _auth_headers(settings)
    async with httpx.AsyncClient(timeout=CHAT_TIMEOUT_SECONDS) as client:
        base_url = settings.agent_server_url.rstrip("/")
        app_name = settings.agent_app_name
        adk_user_id = "metrosense"
        runtime_context = await build_runtime_context(db_session)
        agent_message = _augment_message_with_runtime_context(message, runtime_context)
        try:
            events = await _run_agent_once(
                client=client,
                base_url=base_url,
                app_name=app_name,
                user_id=adk_user_id,
                session_id=session_id,
                message=agent_message,
                headers=headers,
            )
        except httpx.HTTPStatusError as exc:
            if not _is_input_token_limit_error(exc):
                raise
            retry_session_id = _overflow_retry_session_id(session_id)
            logger.warning(
                (
                    "Agent token limit exceeded for session_id={}; "
                    "retrying once with adk_session_id={}"
                ),
                session_id,
                retry_session_id,
            )
            events = await _run_agent_once(
                client=client,
                base_url=base_url,
                app_name=app_name,
                user_id=adk_user_id,
                session_id=retry_session_id,
                message=agent_message,
                headers=headers,
            )

    message_text = _extract_message_from_events(events)
    response_payload = _parse_level2_payload(message_text, session_id=session_id)
    latency_ms = int((time.perf_counter() - started_at) * 1000)

    try:
        await conversation_service.upsert_session(
            db_session,
            session_id=session_id,
            user_id=user_id,
            title=conversation_service.derive_session_title(message),
        )
        assistant_turn_id = await conversation_service.append_turn(
            db_session,
            session_id=session_id,
            user_message=message,
            assistant_message=response_payload["response_text"],
            agents_invoked=[],
            latency_ms=latency_ms,
        )
        db_session.add(
            AuditLog(
                log_id=str(uuid4()),
                session_id=session_id,
                turn_id=assistant_turn_id,
                query_text=message,
                intent_classified=response_payload.get("response_mode"),
                agents_invoked=[],
                overall_confidence=None,
                data_freshness_lag_seconds=None,
                stale_sources=[],
                error_flag=False,
                error_detail=None,
            )
        )
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        logger.exception("Failed to persist conversation history for session_id={}", session_id)

    return response_payload


async def get_agent_health(settings: Settings) -> dict[str, str]:
    headers = _auth_headers(settings)
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{settings.agent_server_url.rstrip('/')}/health",
            headers=headers,
        )
        response.raise_for_status()

    return {"backend": "ok", "agent": "ok", "status": "online"}
