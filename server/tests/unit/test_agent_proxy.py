from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.services import agent_proxy, conversation_service


@pytest.mark.asyncio
async def test_agent_proxy_requires_internal_token() -> None:
    settings = Settings(agent_internal_token="")
    with pytest.raises(ValueError, match="AGENT_INTERNAL_TOKEN"):
        await agent_proxy.get_agent_health(settings)


def test_parse_level2_payload_normalises_string_citations_summary() -> None:
    payload = agent_proxy._parse_level2_payload(
        '{"response_mode":"text","response_text":"Bellandur weather summary generated.",'
        '"citations_summary":["get_weather_summary (Bellandur)"],'
        '"data_freshness_summary":{}}',
        session_id="test-session",
    )

    assert payload["citations_summary"] == [{"source": "get_weather_summary (Bellandur)"}]


def test_parse_level2_payload_normalises_legacy_risk_card_shape() -> None:
    payload = agent_proxy._parse_level2_payload(
        '{"response_mode":"text","response_text":"Risk is elevated.",'
        '"citations_summary":[],"data_freshness_summary":{},'
        '"risk_card":{"location":"Bellandur","as_of":"2026-03-11T00:00:00Z",'
        '"flood_risk":{"score":8,"label":"High","detail":"Flooding likely."},'
        '"outage_risk":{"score":6,"label":"Moderate","detail":"Treefall outages possible."},'
        '"traffic_delay_index":{"score":7,"label":"High","detail":"Slow corridors expected."},'
        '"emergency_readiness":{"score":4,"label":"Reduced","detail":"Keep pumps on standby."},'
        '"advisory":"Avoid low-lying roads."}}',
        session_id="test-session",
    )

    assert payload["risk_card"] == {
        "neighborhood": "Bellandur",
        "generated_at": "2026-03-11T00:00:00Z",
        "overall_risk_score": 6.8,
        "flood_risk": {"probability": 0.8, "severity": "HIGH", "congestion_score": 8.0},
        "power_outage_risk": {
            "probability": 0.6,
            "severity": "MODERATE",
            "congestion_score": 6.0,
        },
        "traffic_delay_index": {
            "probability": 0.7,
            "severity": "HIGH",
            "congestion_score": 7.0,
        },
        "health_advisory": None,
        "emergency_readiness": {
            "recommendation": "Keep pumps on standby.",
            "actions": None,
        },
        "rainfall_expected_mm_per_hr": None,
        "rainfall_classification": None,
        "barricade_recommendations": None,
    }


def test_parse_level2_payload_converts_legacy_weather_comparison_blob_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: Here's a comparison of weather conditions in Bellandur for September and "
        "October 2025. September was wetter and more humid with slightly lower average "
        "temperatures compared to October. details: {'september_2025': {'location': "
        "'Bellandur (zone_east)', 'month': 'September 2025', 'avg_temperature_celsius': 23.3, "
        "'max_temperature_celsius': 31.5, 'min_temperature_celsius': 15.1, "
        "'avg_humidity_pct': 89.0, 'total_rainfall_mm': 697.3, 'readings_count': 2880}, "
        "'october_2025': {'location': 'Bellandur (zone_east)', 'month': 'October 2025', "
        "'avg_temperature_celsius': 24.3, 'max_temperature_celsius': 32.2, "
        "'min_temperature_celsius': 14.0, 'avg_humidity_pct': 78.2, "
        "'total_rainfall_mm': 208.4, 'readings_count': 2976}, 'comparison': "
        "{'temperature_difference': 'October 2025 had a slightly higher average "
        "temperature (+1.0C) than September 2025.'}}. health_advisory: "
        "September's higher humidity suggests higher mosquito risk.",
        session_id="test-session",
    )

    assert payload["response_text"].startswith("Here's a comparison of weather conditions")
    assert payload["response_text"].endswith(
        "Health note: September's higher humidity suggests higher mosquito risk."
    )
    assert payload["artifact"] == {
        "type": "table",
        "title": "Weather Comparison",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Avg Temperature Celsius", 23.3, 24.3],
            ["Max Temperature Celsius", 31.5, 32.2],
            ["Min Temperature Celsius", 15.1, 14.0],
            ["Avg Humidity Pct", 89.0, 78.2],
            ["Total Rainfall Mm", 697.3, 208.4],
            ["Readings Count", 2880, 2976],
            [
                "Temperature Difference",
                "October 2025 had a slightly higher average temperature (+1.0C) than "
                "September 2025.",
                None,
            ],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_comparison_table_blob_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: In Bellandur, October 2025 was slightly warmer with less rainfall and "
        "lower humidity compared to September 2025. details: {'comparison_table': ["
        "{'month': 'September 2025', 'average_temperature_celsius': 23.3, "
        "'max_temperature_celsius': 31.5, 'min_temperature_celsius': 15.1, "
        "'average_humidity_pct': 89.0, 'total_rainfall_mm': 697.3}, "
        "{'month': 'October 2025', 'average_temperature_celsius': 24.3, "
        "'max_temperature_celsius': 32.2, 'min_temperature_celsius': 14.0, "
        "'average_humidity_pct': 78.2, 'total_rainfall_mm': 208.4}]}. "
        "health_advisory: Stay hydrated.",
        session_id="test-session",
    )

    assert payload["artifact"] == {
        "type": "table",
        "title": "Weather Comparison",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature Celsius", 23.3, 24.3],
            ["Max Temperature Celsius", 31.5, 32.2],
            ["Min Temperature Celsius", 15.1, 14.0],
            ["Average Humidity Pct", 89.0, 78.2],
            ["Total Rainfall Mm", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_top_level_comparison_table_json_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        '{"summary":"Comparison ready.","comparison_table":['
        '{"month":"September 2025","average_temperature_celsius":23.3},'
        '{"month":"October 2025","average_temperature_celsius":24.3}'
        "]}",
        session_id="test-session",
    )

    assert payload["response_text"] == "Comparison ready."
    assert payload["artifact"] == {
        "type": "table",
        "title": "Comparison Table",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [["Average Temperature Celsius", 23.3, 24.3]],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_named_table_blob_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: Here's a comparison of weather conditions in Bellandur for September and "
        "October 2025. details: {'Bellandur Weather Comparison (September vs. October 2025)': "
        "[{'Month': 'September 2025', 'Average Temperature (°C)': 23.3, "
        "'Maximum Temperature (°C)': 31.5, 'Minimum Temperature (°C)': 15.1, "
        "'Average Humidity (%)': 89.0, 'Total Rainfall (mm)': 697.3}, "
        "{'Month': 'October 2025', 'Average Temperature (°C)': 24.3, "
        "'Maximum Temperature (°C)': 32.2, 'Minimum Temperature (°C)': 14.0, "
        "'Average Humidity (%)': 78.2, 'Total Rainfall (mm)': 208.4}]}. "
        "health_advisory: Stay hydrated.",
        session_id="test-session",
    )

    assert payload["artifact"] == {
        "type": "table",
        "title": "Bellandur Weather Comparison (September vs. October 2025)",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature (°C)", 23.3, 24.3],
            ["Maximum Temperature (°C)", 31.5, 32.2],
            ["Minimum Temperature (°C)", 15.1, 14.0],
            ["Average Humidity (%)", 89.0, 78.2],
            ["Total Rainfall (mm)", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_malformed_legacy_table_blob_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: Comparing September and October 2025 in Bellandur, October experienced "
        "slightly higher average temperatures and lower humidity. Rainfall significantly "
        "decreased in October, recording 208.4 mm compared to September's 697.3 mm.. "
        "details: {'table': [{'Month': 'September 2025', 'Average Temperature (°C)': 23.3, "
        "'Maximum Temperature (°C)': 31.5, 'Minimum Temperature (°C)': 15.1, "
        "'Average Humidity (%)': 89.0, 'Total Rainfall (mm)': 697.3}, {'Month': 'October 2025', "
        "'Average Temperature (°C)': 24.3, 'Maximum Temperature (°C)': 32.2, "
        "'Minimum Temperature (°C)': 14.0, 'Average Humidity (%)': 78.2, "
        "'Total Rainfall (mm)': 208.4}]}. health_advisory: Given the higher temperatures "
        "and lower humidity in October, general heat precautions are always advisable.",
        session_id="test-session",
    )

    assert payload["response_text"].startswith("Comparing September and October 2025 in Bellandur")
    assert payload["response_text"].endswith(
        "Health note: Given the higher temperatures and lower humidity in October, "
        "general heat precautions are always advisable."
    )
    assert payload["artifact"] == {
        "type": "table",
        "title": "Weather Comparison",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature (°C)", 23.3, 24.3],
            ["Maximum Temperature (°C)", 31.5, 32.2],
            ["Minimum Temperature (°C)", 15.1, 14.0],
            ["Average Humidity (%)", 89.0, 78.2],
            ["Total Rainfall (mm)", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_python_dict_string_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        "{'summary': 'Comparison ready for Bellandur.', 'details': {'table': "
        "[{'Month': 'September 2025', 'Average Temperature (°C)': 23.3, "
        "'Total Rainfall (mm)': 697.3}, {'Month': 'October 2025', "
        "'Average Temperature (°C)': 24.3, 'Total Rainfall (mm)': 208.4}]}, "
        "'health_advisory': 'Stay hydrated.'}",
        session_id="test-session",
    )

    assert (
        payload["response_text"] == "Comparison ready for Bellandur.\n\nHealth note: Stay hydrated."
    )
    assert payload["artifact"] == {
        "type": "table",
        "title": "Weather Comparison",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature (°C)", 23.3, 24.3],
            ["Total Rainfall (mm)", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_columnar_legacy_table_blob_to_table() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: In Bellandur, October 2025 was slightly warmer on average than September "
        "2025, with a higher maximum temperature. However, September experienced "
        "significantly higher rainfall and humidity compared to October.. details: "
        "{'Bellandur Weather Comparison (2025)': {'Metric': ['Average Temperature (°C)', "
        "'Maximum Temperature (°C)', 'Minimum Temperature (°C)', 'Average Humidity (%)', "
        "'Total Rainfall (mm)'], 'September 2025': ['23.3', '31.5', '15.1', '89.0', '697.3'], "
        "'October 2025': ['24.3', '32.2', '14.0', '78.2', '208.4']}}. health_advisory: "
        "Given the higher humidity and significant rainfall in September, there might have "
        "been a higher potential for mold growth and increased discomfort.",
        session_id="test-session",
    )

    assert payload["artifact"] == {
        "type": "table",
        "title": "Bellandur Weather Comparison (2025)",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature (°C)", "23.3", "24.3"],
            ["Maximum Temperature (°C)", "31.5", "32.2"],
            ["Minimum Temperature (°C)", "15.1", "14.0"],
            ["Average Humidity (%)", "89.0", "78.2"],
            ["Total Rainfall (mm)", "697.3", "208.4"],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_extracts_embedded_legacy_table_from_response_text() -> None:
    payload = agent_proxy._parse_level2_payload(
        '{"response_mode":"text","response_text":"summary: Comparing weather in Bellandur for '
        "September and October 2025, September experienced higher average humidity and "
        "significantly more rainfall, while average and maximum temperatures remained similar "
        "across both months. October saw a notable decrease in total rainfall and average "
        "humidity.. details: {'Bellandur Weather Comparison (2025)': {'Metric': ['Average "
        "Temperature (°C)', 'Maximum Temperature (°C)', 'Minimum Temperature (°C)', "
        "'Average Humidity (%)', 'Total Rainfall (mm)'], 'September 2025': [23.3, 31.5, 15.1, "
        "89.0, 697.3], 'October 2025': [24.3, 32.2, 14.0, 78.2, 208.4]}}\","
        '"citations_summary":[{"source":"get_weather_summary (Bellandur)"}],'
        '"data_freshness_summary":{"note":"weather coverage available."},'
        '"risk_card":null,"artifact":null,"follow_up_prompt":null}',
        session_id="test-session",
    )

    assert payload["response_text"].startswith("Comparing weather in Bellandur")
    assert payload["artifact"] == {
        "type": "table",
        "title": "Bellandur Weather Comparison (2025)",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature (°C)", 23.3, 24.3],
            ["Maximum Temperature (°C)", 31.5, 32.2],
            ["Minimum Temperature (°C)", 15.1, 14.0],
            ["Average Humidity (%)", 89.0, 78.2],
            ["Total Rainfall (mm)", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_extracts_embedded_nested_period_table_from_response_text() -> None:
    payload = agent_proxy._parse_level2_payload(
        '{"response_mode":"text","response_text":"summary: Comparing weather in Bellandur for '
        "September and October 2025, September was wetter and slightly cooler with higher "
        "average humidity than October.. details: {'Bellandur_Weather_2025': {'September': "
        "{'avg_temp_c': 23.3, 'max_temp_c': 31.5, 'min_temp_c': 15.1, 'avg_humidity_pct': 89.0, "
        "'total_rainfall_mm': 697.3}, 'October': {'avg_temp_c': 24.3, 'max_temp_c': 32.2, "
        "'min_temp_c': 14.0, 'avg_humidity_pct': 78.2, 'total_rainfall_mm': 208.4}}}. "
        "health_advisory: No specific health advisory is issued based on this weather "
        'comparison alone.","citations_summary":[{"source":"weather summary + Bellandur"}],'
        '"data_freshness_summary":{"note":"coverage available."},"risk_card":null,'
        '"artifact":null,"follow_up_prompt":null}',
        session_id="test-session",
    )

    assert payload["response_text"].startswith("Comparing weather in Bellandur")
    assert payload["artifact"] == {
        "type": "table",
        "title": "Bellandur_Weather_2025",
        "columns": ["Metric", "September", "October"],
        "rows": [
            ["Avg Temp C", 23.3, 24.3],
            ["Max Temp C", 31.5, 32.2],
            ["Min Temp C", 15.1, 14.0],
            ["Avg Humidity Pct", 89.0, 78.2],
            ["Total Rainfall Mm", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level1_payload_extracts_table_artifact_from_data_details() -> None:
    payload = agent_proxy._parse_level2_payload(
        """```json
{
  "agent": "heat_health_agent",
  "query_id": null,
  "timestamp": "2026-03",
  "status": "ok",
  "confidence": 0.9,
  "data": {
    "summary": "In Bellandur, October 2025 was slightly warmer and drier than September 2025.",
    "details": {
      "Bellandur_Weather_2025": [
        {
          "month": "September",
          "avg_humidity_pct": 89.0,
          "avg_temp_c": 23.3,
          "max_temp_c": 31.5,
          "min_temp_c": 15.1,
          "total_rainfall_mm": 697.3
        },
        {
          "month": "October",
          "avg_humidity_pct": 78.2,
          "avg_temp_c": 24.3,
          "max_temp_c": 32.2,
          "min_temp_c": 14.0,
          "total_rainfall_mm": 208.4
        }
      ]
    },
    "health_advisory": "Stay hydrated."
  },
  "citations": ["get_weather_summary - Bellandur"],
  "data_freshness": "coverage available",
  "context_used": ["weather"],
  "errors": []
}
```""",
        session_id="test-session",
    )

    assert payload["response_text"] == (
        "In Bellandur, October 2025 was slightly warmer and drier than September 2025.\n\n"
        "Health note: Stay hydrated."
    )
    assert payload["artifact"] == {
        "type": "table",
        "title": "Bellandur_Weather_2025",
        "columns": ["Metric", "September", "October"],
        "rows": [
            ["Avg Humidity Pct", 89.0, 78.2],
            ["Avg Temp C", 23.3, 24.3],
            ["Max Temp C", 31.5, 32.2],
            ["Min Temp C", 15.1, 14.0],
            ["Total Rainfall Mm", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_metric_row_comparison_table_blob() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: In Bellandur during 2025, October experienced slightly higher average "
        "temperatures and maximum temperatures compared to September, while September had "
        "significantly higher total rainfall and average humidity.. details: {'September 2025': "
        "{'Average Temperature': '23.3 °C', 'Maximum Temperature': '31.5 °C', "
        "'Minimum Temperature': '15.1 °C', 'Average Humidity': '89%', 'Total Rainfall': "
        "'697.3 mm'}, 'October 2025': {'Average Temperature': '24.3 °C', 'Maximum Temperature': "
        "'32.2 °C', 'Minimum Temperature': '14.0 °C', 'Average Humidity': '78.2%', "
        "'Total Rainfall': '208.4 mm'}, 'comparison_table': [{'Metric': 'Month', "
        "'September 2025': 'September', 'October 2025': 'October'}, {'Metric': "
        "'Average Temperature (°C)', 'September 2025': '23.3', 'October 2025': '24.3'}, "
        "{'Metric': 'Maximum Temperature (°C)', 'September 2025': '31.5', 'October 2025': "
        "'32.2'}, {'Metric': 'Minimum Temperature (°C)', 'September 2025': '15.1', "
        "'October 2025': '14.0'}, {'Metric': 'Average Humidity (%)', 'September 2025': '89.0', "
        "'October 2025': '78.2'}, {'Metric': 'Total Rainfall (mm)', 'September 2025': '697.3', "
        "'October 2025': '208.4'}]}. health_advisory: Stay hydrated.",
        session_id="test-session",
    )

    assert payload["artifact"] == {
        "type": "table",
        "title": "Weather Comparison",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Month", "September", "October"],
            ["Average Temperature (°C)", "23.3", "24.3"],
            ["Maximum Temperature (°C)", "31.5", "32.2"],
            ["Minimum Temperature (°C)", "15.1", "14.0"],
            ["Average Humidity (%)", "89.0", "78.2"],
            ["Total Rainfall (mm)", "697.3", "208.4"],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_month_column_table_blob() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: In Bellandur, October 2025 was slightly warmer and less humid with "
        "significantly less rainfall compared to September 2025.. details: {'Bellandur "
        "Weather Comparison (2025)': {'Month': ['September', 'October'], "
        "'Average Temperature (°C)': [23.3, 24.3], 'Maximum Temperature (°C)': [31.5, 32.2], "
        "'Minimum Temperature (°C)': [15.1, 14.0], 'Average Humidity (%)': [89.0, 78.2], "
        "'Total Rainfall (mm)': [697.3, 208.4]}}",
        session_id="test-session",
    )

    assert payload["artifact"] == {
        "type": "table",
        "title": "Bellandur Weather Comparison (2025)",
        "columns": ["Metric", "September", "October"],
        "rows": [
            ["Average Temperature (°C)", 23.3, 24.3],
            ["Maximum Temperature (°C)", 31.5, 32.2],
            ["Minimum Temperature (°C)", 15.1, 14.0],
            ["Average Humidity (%)", 89.0, 78.2],
            ["Total Rainfall (mm)", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


def test_parse_level2_payload_converts_headers_rows_table_blob() -> None:
    payload = agent_proxy._parse_level2_payload(
        "summary: In Bellandur, October 2025 was slightly warmer with a higher average and "
        "maximum temperature, and significantly less rainfall compared to September 2025.. "
        "details: {'table_comparison': {'headers': ['Metric', 'September 2025', 'October 2025'], "
        "'rows': [['Average Temperature (°C)', 23.3, 24.3], ['Maximum Temperature (°C)', 31.5, "
        "32.2], ['Minimum Temperature (°C)', 15.1, 14.0], ['Average Humidity (%)', 89.0, 78.2], "
        "['Total Rainfall (mm)', 697.3, 208.4]]}}",
        session_id="test-session",
    )

    assert payload["artifact"] == {
        "type": "table",
        "title": "table_comparison",
        "columns": ["Metric", "September 2025", "October 2025"],
        "rows": [
            ["Average Temperature (°C)", 23.3, 24.3],
            ["Maximum Temperature (°C)", 31.5, 32.2],
            ["Minimum Temperature (°C)", 15.1, 14.0],
            ["Average Humidity (%)", 89.0, 78.2],
            ["Total Rainfall (mm)", 697.3, 208.4],
        ],
        "description": "Month-over-month comparison generated from MetroSense weather summaries.",
    }


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_payload: Any = None,
        should_raise: bool = False,
    ) -> None:
        self.status_code = status_code
        self._json_payload = json_payload
        self._should_raise = should_raise

    def json(self) -> Any:
        return self._json_payload

    def raise_for_status(self) -> None:
        if self._should_raise:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", "http://test/run"),
                response=httpx.Response(500),
            )


class _FakeAsyncClient:
    def __init__(self, *_: object, **__: object) -> None:
        self._call_count = 0

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(self, *_: object, **__: object) -> _FakeResponse:
        self._call_count += 1
        if self._call_count == 1:
            return _FakeResponse(status_code=201)
        return _FakeResponse(
            json_payload=[
                {"content": {"role": "model", "parts": [{"text": "Persisted assistant reply"}]}}
            ]
        )


class _OverflowThenSuccessClient:
    def __init__(self, *_: object, **__: object) -> None:
        self._call_count = 0

    async def __aenter__(self) -> _OverflowThenSuccessClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(self, url: str, *_: object, **kwargs: object) -> _FakeResponse:
        self._call_count += 1
        if self._call_count in {1, 3}:
            return _FakeResponse(status_code=201)
        if self._call_count == 2:
            payload = {
                "error": {
                    "code": 400,
                    "message": (
                        "The input token count exceeds the maximum number of tokens "
                        "allowed (1048576)."
                    ),
                    "status": "INVALID_ARGUMENT",
                }
            }
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("POST", url),
                response=httpx.Response(400, json=payload, request=httpx.Request("POST", url)),
            )
        assert self._call_count == 4
        body = kwargs.get("json")
        assert isinstance(body, dict)
        assert isinstance(body.get("sessionId"), str)
        assert "--retry-" in body["sessionId"]
        return _FakeResponse(
            json_payload=[
                {"content": {"role": "model", "parts": [{"text": "Reply after overflow reset"}]}}
            ]
        )


class _CaptureMessageClient:
    last_message: str | None = None

    def __init__(self, *_: object, **__: object) -> None:
        self._call_count = 0

    async def __aenter__(self) -> _CaptureMessageClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def post(self, *_: object, **kwargs: object) -> _FakeResponse:
        self._call_count += 1
        if self._call_count == 1:
            return _FakeResponse(status_code=201)
        body = kwargs.get("json")
        assert isinstance(body, dict)
        new_message = body.get("newMessage")
        assert isinstance(new_message, dict)
        parts = new_message.get("parts")
        assert isinstance(parts, list)
        text_part = parts[0]
        assert isinstance(text_part, dict)
        _CaptureMessageClient.last_message = text_part.get("text")
        return _FakeResponse(
            json_payload=[
                {"content": {"role": "model", "parts": [{"text": "Persisted assistant reply"}]}}
            ]
        )


@pytest.mark.asyncio
async def test_get_chat_response_persists_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    db_session.add = MagicMock()
    upsert = AsyncMock()
    append = AsyncMock(return_value="turn-id")

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(conversation_service, "session_owner_id", AsyncMock(return_value=None))
    monkeypatch.setattr(conversation_service, "derive_session_title", lambda _: "Hello title")
    monkeypatch.setattr(conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(conversation_service, "append_turn", append)
    monkeypatch.setattr(
        agent_proxy,
        "build_runtime_context",
        AsyncMock(return_value={"generated_at": "2026-03-11T00:00:00+00:00", "domains": {}}),
    )

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-1",
        message="hello",
    )

    assert payload["message"] == "Persisted assistant reply"
    assert payload["response_text"] == "Persisted assistant reply"
    assert payload["session_id"] == "s-1"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.commit.assert_awaited_once()
    db_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_append_turn_flushes_before_audit_log_fk_is_used() -> None:
    db_session = AsyncMock()
    db_session.add_all = MagicMock()

    turn_id = await conversation_service.append_turn(
        session=db_session,
        session_id="s-1",
        user_message="hello",
        assistant_message="world",
        agents_invoked=[],
        latency_ms=10,
    )

    assert isinstance(turn_id, str)
    db_session.add_all.assert_called_once()
    db_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_chat_response_returns_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    db_session.add = MagicMock()
    upsert = AsyncMock()
    append = AsyncMock(side_effect=RuntimeError("db write failure"))

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(conversation_service, "session_owner_id", AsyncMock(return_value=None))
    monkeypatch.setattr(conversation_service, "derive_session_title", lambda _: "Hello title")
    monkeypatch.setattr(conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(conversation_service, "append_turn", append)
    monkeypatch.setattr(
        agent_proxy,
        "build_runtime_context",
        AsyncMock(return_value={"generated_at": "2026-03-11T00:00:00+00:00", "domains": {}}),
    )

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-2",
        message="hello",
    )

    assert payload["message"] == "Persisted assistant reply"
    assert payload["response_text"] == "Persisted assistant reply"
    assert payload["session_id"] == "s-2"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.rollback.assert_awaited_once()
    db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_chat_response_retries_once_on_input_token_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    db_session.add = MagicMock()
    upsert = AsyncMock()
    append = AsyncMock(return_value="turn-id")

    monkeypatch.setattr(httpx, "AsyncClient", _OverflowThenSuccessClient)
    monkeypatch.setattr(conversation_service, "session_owner_id", AsyncMock(return_value=None))
    monkeypatch.setattr(conversation_service, "derive_session_title", lambda _: "Hello title")
    monkeypatch.setattr(conversation_service, "upsert_session", upsert)
    monkeypatch.setattr(conversation_service, "append_turn", append)
    monkeypatch.setattr(
        agent_proxy,
        "build_runtime_context",
        AsyncMock(return_value={"generated_at": "2026-03-11T00:00:00+00:00", "domains": {}}),
    )

    payload = await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-overflow",
        message="hello",
    )

    assert payload["message"] == "Reply after overflow reset"
    assert payload["response_text"] == "Reply after overflow reset"
    assert payload["session_id"] == "s-overflow"
    upsert.assert_awaited_once()
    append.assert_awaited_once()
    db_session.commit.assert_awaited_once()
    db_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_chat_response_injects_runtime_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        agent_internal_token="test-token",
        agent_server_url="http://agent.local",
    )
    db_session = AsyncMock()
    db_session.add = MagicMock()

    monkeypatch.setattr(httpx, "AsyncClient", _CaptureMessageClient)
    monkeypatch.setattr(conversation_service, "session_owner_id", AsyncMock(return_value=None))
    monkeypatch.setattr(conversation_service, "derive_session_title", lambda _: "Hello title")
    monkeypatch.setattr(conversation_service, "upsert_session", AsyncMock())
    monkeypatch.setattr(conversation_service, "append_turn", AsyncMock(return_value="turn-id"))
    monkeypatch.setattr(
        agent_proxy,
        "build_runtime_context",
        AsyncMock(return_value={"generated_at": "2026-03-11T00:00:00+00:00", "domains": {}}),
    )

    await agent_proxy.get_chat_response(
        settings=settings,
        db_session=db_session,
        user_id=1,
        session_id="s-ctx",
        message="show me Bellandur flood risk",
    )

    captured = _CaptureMessageClient.last_message
    assert captured is not None
    assert "[MetroSense Runtime Context]" in captured
    assert '"generated_at":"2026-03-11T00:00:00+00:00"' in captured
    assert "[User Message]\nshow me Bellandur flood risk" in captured
