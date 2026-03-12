from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

# Allow direct script execution via:
# `uv run python scripts/load_metrosense_dataset.py --replace`
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import SERVER_DIR, get_settings

DATASET_DIR = SERVER_DIR / "DataSet_MetroSense"
DOCUMENTS_DIR = SERVER_DIR / "Documents_Metrosense"
IST = ZoneInfo("Asia/Kolkata")

DATASET_TABLE_ORDER = [
    "air_quality_observation",
    "weather_observation",
    "flood_incident",
    "power_outage_event",
    "traffic_segment_observation",
    "lake_hydrology",
    "ward_profile",
    "lake_reference",
    "location_master",
]

CSV_TABLES = {
    "air_quality_observations.csv": "air_quality_observation",
    "weather_observations.csv": "weather_observation",
    "flood_incidents.csv": "flood_incident",
    "power_outage_events.csv": "power_outage_event",
    "traffic_segment_observations.csv": "traffic_segment_observation",
    "lake_hydrology.csv": "lake_hydrology",
}

LAKE_NAME_BY_ID = {
    "lake_001": "Bellandur",
    "lake_002": "Varthur",
    "lake_003": "Hebbal",
    "lake_004": "Nagavara",
    "lake_005": "KR Puram",
    "lake_006": "Madiwala",
}


@dataclass
class FactReferences:
    location_ids: set[str]
    ward_ids: set[str]
    lake_ids: set[str]


class LoaderValidationError(RuntimeError):
    pass


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt


def _to_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    raise LoaderValidationError(f"Unexpected boolean literal: {value}")


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _to_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _norm(value: str) -> str:
    return " ".join(value.strip().split()).lower()


def _display_name_from_zone(zone_id: str) -> str:
    if not zone_id.startswith("zone_"):
        return zone_id
    return zone_id.replace("zone_", "").replace("_", " ").title()


def _load_document_names() -> set[str]:
    names: set[str] = set()
    for index_file in DOCUMENTS_DIR.glob("*_index.json"):
        payload = json.loads(index_file.read_text())
        names.update(payload.get("wards_covered", []))
        for section in payload.get("table_of_contents", []):
            names.update(section.get("wards_mentioned", []))
    return names


def _collect_references() -> tuple[FactReferences, dict[str, str], dict[str, str]]:
    location_ids: set[str] = set()
    ward_ids: set[str] = set()
    lake_ids: set[str] = set()
    ward_name_by_id: dict[str, str] = {}
    zone_name_by_ward_id: dict[str, str] = {}

    for csv_name in CSV_TABLES:
        with (DATASET_DIR / csv_name).open(newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                location = (row.get("location_id") or "").strip()
                if location:
                    location_ids.add(location)

                ward = (row.get("ward_id") or "").strip()
                if ward:
                    ward_ids.add(ward)

                lake = (row.get("lake_id") or "").strip()
                if lake:
                    lake_ids.add(lake)

                if csv_name == "air_quality_observations.csv":
                    if ward and location and not ward.startswith("zone_"):
                        ward_name_by_id[ward] = location

                if csv_name == "flood_incidents.csv":
                    if ward and (row.get("neighborhood_name") or "").strip():
                        ward_name_by_id.setdefault(ward, row["neighborhood_name"].strip())

                if csv_name == "power_outage_events.csv":
                    if ward and (row.get("zone_name") or "").strip():
                        zone_name_by_ward_id[ward] = row["zone_name"].strip()

    return (
        FactReferences(location_ids=location_ids, ward_ids=ward_ids, lake_ids=lake_ids),
        ward_name_by_id,
        zone_name_by_ward_id,
    )


def _build_location_rows(
    refs: FactReferences,
    ward_name_by_id: dict[str, str],
    zone_name_by_ward_id: dict[str, str],
) -> list[dict[str, Any]]:
    now = datetime.now().astimezone()
    all_known_names = _load_document_names()
    canonical_name_by_norm = {_norm(name): name for name in all_known_names}
    rows: list[dict[str, Any]] = []

    for ward_id in sorted(refs.ward_ids):
        ward_name = ward_name_by_id.get(ward_id)
        zone_name = zone_name_by_ward_id.get(ward_id)
        canonical = ward_name or ward_id
        alias_set = {canonical, ward_id.replace("_", " ")}
        rows.append(
            {
                "location_id": ward_id,
                "canonical_name": canonical,
                "location_type": "ward",
                "aliases": sorted(alias_set),
                "ward_id": ward_id,
                "ward_name": ward_name,
                "zone_name": zone_name,
                "neighborhood_name": ward_name,
                "pin_code": None,
                "latitude": None,
                "longitude": None,
                "geometry": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    for location_id in sorted(refs.location_ids):
        if location_id in refs.ward_ids:
            continue

        loc_ward_id: str | None = None
        loc_ward_name: str | None = None
        loc_zone_name: str | None = None
        loc_neighborhood_name: str | None = None

        if location_id.startswith("zone_"):
            canonical = _display_name_from_zone(location_id)
            loc_type = "zone"
            loc_zone_name = location_id
        else:
            normalized = _norm(location_id)
            canonical = canonical_name_by_norm.get(normalized, location_id)
            loc_type = "neighborhood"
            loc_neighborhood_name = canonical

        rows.append(
            {
                "location_id": location_id,
                "canonical_name": canonical,
                "location_type": loc_type,
                "aliases": sorted({canonical, location_id}),
                "ward_id": loc_ward_id,
                "ward_name": loc_ward_name,
                "zone_name": loc_zone_name,
                "neighborhood_name": loc_neighborhood_name,
                "pin_code": None,
                "latitude": None,
                "longitude": None,
                "geometry": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    return rows


def _build_ward_profile_rows(ward_ids: set[str]) -> list[dict[str, Any]]:
    return [
        {
            "profile_id": f"profile_{ward_id}",
            "ward_id": ward_id,
            "population_density": None,
            "elderly_population_pct": None,
            "children_population_pct": None,
            "slum_household_count": None,
            "green_cover_pct": None,
            "impervious_surface_pct": None,
            "data_year": None,
            "source_name": "Documents_Metrosense",
        }
        for ward_id in sorted(ward_ids)
    ]


def _build_lake_reference_rows(
    lake_ids: set[str],
    known_location_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lake_id in sorted(lake_ids):
        lake_name = LAKE_NAME_BY_ID.get(lake_id, lake_id)
        rows.append(
            {
                "lake_id": lake_id,
                "lake_name": lake_name,
                "lake_type": None,
                "location_id": lake_name if lake_name in known_location_ids else None,
                "ward_id": None,
                "latitude": None,
                "longitude": None,
                "catchment_area_sqkm": None,
                "lake_area_sqkm": None,
                "full_tank_level_meters": None,
                "max_capacity_mcm": None,
                "number_of_gates": None,
                "source_name": "Documents_Metrosense",
            }
        )
    return rows


def _validate_location_coverage(location_rows: list[dict[str, Any]], refs: FactReferences) -> None:
    canonical_ids = {row["location_id"] for row in location_rows}
    missing_locations = sorted(refs.location_ids - canonical_ids)
    missing_wards = sorted(refs.ward_ids - canonical_ids)

    if missing_locations or missing_wards:
        detail = {
            "missing_location_ids": missing_locations[:20],
            "missing_ward_ids": missing_wards[:20],
            "missing_location_count": len(missing_locations),
            "missing_ward_count": len(missing_wards),
        }
        raise LoaderValidationError(
            "Location normalization failed coverage check: " + json.dumps(detail, sort_keys=True)
        )


def _transform_row(table_name: str, row: dict[str, str]) -> dict[str, Any]:
    transformed: dict[str, Any] = {
        key: (value if value != "" else None) for key, value in row.items()
    }

    if table_name == "weather_observation":
        transformed["observed_at"] = _parse_timestamp(row["observed_at"])
        transformed["ingested_at"] = _parse_timestamp(row["ingested_at"])
        transformed["elevation_meters"] = _to_float(row.get("elevation_meters"))
        transformed["temperature_celsius"] = _to_float(row.get("temperature_celsius"))
        transformed["humidity_percent"] = _to_float(row.get("humidity_percent"))
        transformed["pressure_hpa"] = _to_float(row.get("pressure_hpa"))
        transformed["wind_speed_kmh"] = _to_float(row.get("wind_speed_kmh"))
        transformed["wind_gust_kmh"] = _to_float(row.get("wind_gust_kmh"))
        transformed["wind_direction_degrees"] = _to_int(row.get("wind_direction_degrees"))
        transformed["rainfall_mm_hourly"] = _to_float(row.get("rainfall_mm_hourly"))
        transformed["rainfall_mm_24hour"] = _to_float(row.get("rainfall_mm_24hour"))
        transformed["rainfall_intensity_mm_hr"] = _to_float(row.get("rainfall_intensity_mm_hr"))
        transformed["visibility_km"] = _to_float(row.get("visibility_km"))
        transformed["latitude"] = _to_float(row.get("latitude"))
        transformed["longitude"] = _to_float(row.get("longitude"))

    elif table_name == "air_quality_observation":
        transformed["observed_at"] = _parse_timestamp(row["observed_at"])
        transformed["ingested_at"] = _parse_timestamp(row["ingested_at"])
        for col in ["pm2_5", "pm10", "no2", "so2", "co", "ozone", "nh3", "latitude", "longitude"]:
            transformed[col] = _to_float(row.get(col))
        transformed["aqi_value"] = _to_int(row.get("aqi_value"))

    elif table_name == "lake_hydrology":
        transformed["observed_at"] = _parse_timestamp(row["observed_at"])
        transformed["ingested_at"] = _parse_timestamp(row["ingested_at"])
        for col in [
            "water_level_meters",
            "fill_percentage",
            "inflow_cusecs",
            "outflow_cusecs",
            "surplus_flow_cusecs",
            "rainfall_last_1h_mm",
            "rainfall_last_24h_mm",
        ]:
            transformed[col] = _to_float(row.get(col))
        transformed["overflow_status"] = _to_bool(row.get("overflow_status"))
        transformed["encroachment_risk_flag"] = _to_bool(row.get("encroachment_risk_flag"))
        transformed["siltation_risk_flag"] = _to_bool(row.get("siltation_risk_flag"))
        transformed["number_of_gates_open"] = _to_int(row.get("number_of_gates_open"))

    elif table_name == "power_outage_event":
        transformed["started_at"] = _parse_timestamp(row["started_at"])
        transformed["restored_at"] = _parse_timestamp(row.get("restored_at"))
        transformed["duration_minutes"] = _to_int(row.get("duration_minutes"))
        transformed["affected_customers"] = _to_int(row.get("affected_customers"))
        transformed["critical_load_affected_flag"] = _to_bool(
            row.get("critical_load_affected_flag")
        )
        for col in [
            "wind_speed_kmh_at_time",
            "wind_gust_kmh_at_time",
            "rainfall_mm_1h_at_time",
            "rainfall_mm_24h_at_time",
        ]:
            transformed[col] = _to_float(row.get(col))

    elif table_name == "traffic_segment_observation":
        transformed["observed_at"] = _parse_timestamp(row["observed_at"])
        transformed["ingested_at"] = _parse_timestamp(row["ingested_at"])
        transformed["lanes_count"] = _to_int(row.get("lanes_count"))
        for col in [
            "speed_limit_kmh",
            "avg_speed_kmh",
            "free_flow_speed_kmh",
            "travel_time_minutes",
            "free_flow_travel_time_minutes",
            "delay_minutes",
            "congestion_index",
            "heavy_vehicle_share",
            "rainfall_mm_1h_at_time",
            "rainfall_mm_3h_at_time",
        ]:
            transformed[col] = _to_float(row.get(col))
        transformed["waterlogging_flag"] = _to_bool(row.get("waterlogging_flag"))

    elif table_name == "flood_incident":
        transformed["reported_at"] = _parse_timestamp(row["reported_at"])
        transformed["resolved_at"] = _parse_timestamp(row.get("resolved_at"))
        for col in [
            "latitude",
            "longitude",
            "water_depth_cm",
            "rainfall_mm_1h_at_time",
            "rainfall_mm_3h_at_time",
        ]:
            transformed[col] = _to_float(row.get(col))
        for col in [
            "road_blocked_flag",
            "vehicles_stranded_flag",
            "property_damage_flag",
            "pump_deployed_flag",
        ]:
            transformed[col] = _to_bool(row.get(col))

    return transformed


async def _insert_rows(
    conn: AsyncConnection,
    table_name: str,
    rows: list[dict[str, Any]],
    batch_size: int = 5000,
) -> int:
    if not rows:
        return 0

    columns = list(rows[0].keys())
    col_sql = ", ".join(columns)
    value_sql = ", ".join(f":{col}" for col in columns)
    statement = text(f"INSERT INTO {table_name} ({col_sql}) VALUES ({value_sql})")

    inserted = 0
    for start in range(0, len(rows), batch_size):
        raw_batch = rows[start : start + batch_size]
        batch: list[dict[str, Any]] = []
        for row in raw_batch:
            normalized_row: dict[str, Any] = {}
            for key, value in row.items():
                if isinstance(value, list | dict):
                    normalized_row[key] = json.dumps(value)
                else:
                    normalized_row[key] = value
            batch.append(normalized_row)
        await conn.execute(statement, batch)
        inserted += len(batch)
    return inserted


async def _load_csv_table(
    conn: AsyncConnection,
    csv_name: str,
    table_name: str,
    batch_size: int = 5000,
) -> int:
    inserted = 0
    batch: list[dict[str, Any]] = []

    with (DATASET_DIR / csv_name).open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            batch.append(_transform_row(table_name, row))
            if len(batch) >= batch_size:
                inserted += await _insert_rows(conn, table_name, batch, batch_size=batch_size)
                batch = []

    if batch:
        inserted += await _insert_rows(conn, table_name, batch, batch_size=batch_size)

    return inserted


async def run_loader(
    replace: bool, simulate_failure_after_truncate: bool = False
) -> dict[str, int]:
    settings = get_settings()
    engine = create_async_engine(settings.effective_db_url)

    refs, ward_name_by_id, zone_name_by_ward_id = _collect_references()
    location_rows = _build_location_rows(refs, ward_name_by_id, zone_name_by_ward_id)
    _validate_location_coverage(location_rows, refs)
    ward_profile_rows = _build_ward_profile_rows(refs.ward_ids)
    lake_reference_rows = _build_lake_reference_rows(refs.lake_ids, refs.location_ids)

    # Explicit diagnostics before SQL FKs fire to highlight normalization issues.
    lake_reference_ids = {row["lake_id"] for row in lake_reference_rows}
    missing_lakes = sorted(refs.lake_ids - lake_reference_ids)
    if missing_lakes:
        raise LoaderValidationError(
            f"Missing lake_reference rows for lake_ids: {missing_lakes[:20]}"
        )

    inserted_counts: defaultdict[str, int] = defaultdict(int)

    async with engine.begin() as conn:
        await conn.execute(text("SET LOCAL TIME ZONE 'Asia/Kolkata'"))
        if replace:
            truncate_sql = "TRUNCATE TABLE " + ", ".join(DATASET_TABLE_ORDER) + " RESTART IDENTITY"
            await conn.execute(text(truncate_sql))

        if simulate_failure_after_truncate:
            raise RuntimeError("Simulated loader failure after truncate")

        inserted_counts["location_master"] = await _insert_rows(
            conn,
            "location_master",
            location_rows,
            batch_size=2000,
        )
        inserted_counts["ward_profile"] = await _insert_rows(
            conn,
            "ward_profile",
            ward_profile_rows,
            batch_size=2000,
        )
        inserted_counts["lake_reference"] = await _insert_rows(
            conn,
            "lake_reference",
            lake_reference_rows,
            batch_size=2000,
        )

        for csv_name, table_name in CSV_TABLES.items():
            inserted_counts[table_name] = await _load_csv_table(conn, csv_name, table_name)

    await engine.dispose()
    return dict(inserted_counts)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load MetroSense golden CSV dataset into Postgres")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate dataset tables before loading so DB mirrors golden CSVs",
    )
    parser.add_argument(
        "--simulate-failure-after-truncate",
        action="store_true",
        help="Crash after truncate to validate transaction rollback behavior",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not args.replace:
        raise SystemExit(
            "Refusing to run without --replace. "
            "This loader is designed for golden data replacement."
        )

    import asyncio

    inserted = asyncio.run(
        run_loader(
            replace=args.replace,
            simulate_failure_after_truncate=args.simulate_failure_after_truncate,
        )
    )
    print(json.dumps(inserted, sort_keys=True))


if __name__ == "__main__":
    main()
