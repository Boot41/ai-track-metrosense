from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect

from app.db.models import (
    AirQualityObservation,
    FloodIncident,
    LakeHydrology,
    LocationMaster,
    PowerOutageEvent,
    TrafficSegmentObservation,
    WardProfile,
    WeatherObservation,
)

# ---------------------------------------------------------------------------
# Neighbourhood → zone mapping for weather and traffic lookups.
# Weather and traffic data are stored per zone (zone_north/east/south/west/cbd)
# while other domains use plain neighbourhood names or ward_ids.
# ---------------------------------------------------------------------------
_NEIGHBORHOOD_ZONE_MAP: dict[str, str] = {
    "Hebbal": "zone_north",
    "Manyata Tech Park": "zone_north",
    "Yelahanka": "zone_north",
    "KR Puram": "zone_east",
    "Whitefield": "zone_east",
    "Varthur": "zone_east",
    "Bellandur": "zone_east",
    "Koramangala": "zone_south",
    "BTM Layout": "zone_south",
    "Jayanagar": "zone_south",
    "Silk Board": "zone_south",
    "Sarjapur": "zone_south",
    "Peenya": "zone_west",
    "Rajajinagar": "zone_west",
    "Yeshwanthpur": "zone_west",
    "MG Road": "zone_cbd",
    "Indiranagar": "zone_cbd",
}


def _row_to_dict(row: Any) -> dict[str, Any]:
    mapper = inspect(type(row))
    payload: dict[str, Any] = {}
    for column in mapper.columns:
        payload[column.key] = getattr(row, column.key)
    return payload


async def _resolve_zone_id(session: AsyncSession, location_id: str) -> str:
    """Resolve a neighbourhood name or ward_id to the zone_id used in weather/traffic tables.

    Falls back to the original value if no mapping can be found so that
    callers passing a zone_id directly still work.
    """
    if location_id.startswith("zone_"):
        return location_id
    # Fast static lookup by canonical name
    if location_id in _NEIGHBORHOOD_ZONE_MAP:
        return _NEIGHBORHOOD_ZONE_MAP[location_id]
    # Try location_master zone_name (covers entries seeded with a zone)
    stmt = (
        select(LocationMaster.zone_name)
        .where(
            or_(
                LocationMaster.location_id == location_id,
                LocationMaster.canonical_name == location_id,
            ),
            LocationMaster.zone_name.is_not(None),
        )
        .limit(1)
    )
    zone: str | None = (await session.execute(stmt)).scalar()
    if zone:
        return zone
    # Fall back: try to match the canonical_name against the static map
    name_stmt = (
        select(LocationMaster.canonical_name)
        .where(LocationMaster.location_id == location_id)
        .limit(1)
    )
    canonical: str | None = (await session.execute(name_stmt)).scalar()
    return _NEIGHBORHOOD_ZONE_MAP.get(canonical or "", location_id)


async def resolve_zone_id(session: AsyncSession, location_id: str) -> str:
    return await _resolve_zone_id(session, location_id)


async def _resolve_ward_id(session: AsyncSession, location_id: str) -> str:
    """Resolve a neighbourhood name or plain location_id to its ward_id.

    Flood and outage data are stored using ward_ids (e.g. ward_007).
    """
    if location_id.startswith("ward_"):
        return location_id
    stmt = (
        select(LocationMaster.location_id)
        .where(
            or_(
                LocationMaster.location_id == location_id,
                LocationMaster.canonical_name == location_id,
            ),
            LocationMaster.location_type == "ward",
        )
        .limit(1)
    )
    ward: str | None = (await session.execute(stmt)).scalar()
    return ward if ward else location_id


async def resolve_ward_id(session: AsyncSession, location_id: str) -> str:
    return await _resolve_ward_id(session, location_id)


async def _dataset_anchor(session: AsyncSession, ts_col: Any) -> datetime:
    """Return MAX(ts_col) as the reference anchor for historical window queries.

    Using the dataset's own latest timestamp instead of datetime.now() means
    static / historical datasets remain queryable regardless of when the server runs.
    """
    result = await session.execute(select(func.max(ts_col)))
    anchor: datetime | None = result.scalar()
    return anchor if anchor is not None else datetime.now(UTC)


async def get_weather_current(
    session: AsyncSession, location_id: str, limit: int = 1
) -> list[dict[str, Any]]:
    zone_id = await _resolve_zone_id(session, location_id)
    stmt = (
        select(WeatherObservation)
        .where(WeatherObservation.location_id == zone_id)
        .order_by(WeatherObservation.observed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_weather_historical(
    session: AsyncSession, location_id: str, hours: int = 720
) -> list[dict[str, Any]]:
    zone_id = await _resolve_zone_id(session, location_id)
    anchor = await _dataset_anchor(session, WeatherObservation.observed_at)
    window_start = anchor - timedelta(hours=hours)
    stmt = (
        select(WeatherObservation)
        .where(
            WeatherObservation.location_id == zone_id,
            WeatherObservation.observed_at >= window_start,
        )
        .order_by(WeatherObservation.observed_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_aqi_current(
    session: AsyncSession, location_id: str, limit: int = 1
) -> list[dict[str, Any]]:
    stmt = (
        select(AirQualityObservation)
        .where(AirQualityObservation.location_id == location_id)
        .order_by(AirQualityObservation.observed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_aqi_historical(
    session: AsyncSession, location_id: str, days: int = 365
) -> list[dict[str, Any]]:
    anchor = await _dataset_anchor(session, AirQualityObservation.observed_at)
    window_start = anchor - timedelta(days=days)
    stmt = (
        select(AirQualityObservation)
        .where(
            AirQualityObservation.location_id == location_id,
            AirQualityObservation.observed_at >= window_start,
        )
        .order_by(AirQualityObservation.observed_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_lake_hydrology(
    session: AsyncSession, lake_id: str, limit: int = 5
) -> list[dict[str, Any]]:
    stmt = (
        select(LakeHydrology)
        .where(LakeHydrology.lake_id == lake_id)
        .order_by(LakeHydrology.observed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_flood_incidents(
    session: AsyncSession, location_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    ward_id = await _resolve_ward_id(session, location_id)
    stmt = (
        select(FloodIncident)
        .where(FloodIncident.location_id == ward_id)
        .order_by(FloodIncident.reported_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_power_outages(
    session: AsyncSession, location_id: str, window_days: int = 365
) -> list[dict[str, Any]]:
    ward_id = await _resolve_ward_id(session, location_id)
    anchor = await _dataset_anchor(session, PowerOutageEvent.started_at)
    window_start = anchor - timedelta(days=window_days)
    stmt = (
        select(PowerOutageEvent)
        .where(
            PowerOutageEvent.location_id == ward_id,
            PowerOutageEvent.started_at >= window_start,
            or_(
                PowerOutageEvent.outage_type.is_(None),
                func.lower(PowerOutageEvent.outage_type) != "planned",
            ),
        )
        .order_by(PowerOutageEvent.started_at.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_traffic_current(
    session: AsyncSession, location_id: str, limit: int = 5
) -> list[dict[str, Any]]:
    zone_id = await _resolve_zone_id(session, location_id)
    stmt = (
        select(TrafficSegmentObservation)
        .where(TrafficSegmentObservation.location_id == zone_id)
        .order_by(TrafficSegmentObservation.observed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_traffic_corridor(
    session: AsyncSession, corridor_name: str, limit: int = 20
) -> list[dict[str, Any]]:
    stmt = (
        select(TrafficSegmentObservation)
        .where(func.lower(TrafficSegmentObservation.corridor_name) == corridor_name.lower())
        .order_by(TrafficSegmentObservation.observed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def resolve_location(session: AsyncSession, name: str) -> list[dict[str, Any]]:
    pattern = f"%{name}%"
    stmt = (
        select(LocationMaster)
        .where(
            or_(
                LocationMaster.canonical_name.ilike(pattern),
                cast(LocationMaster.aliases, String).ilike(pattern),
            )
        )
        .order_by(LocationMaster.canonical_name.asc())
        .limit(20)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def list_locations(session: AsyncSession, limit: int = 200) -> list[dict[str, Any]]:
    stmt = select(LocationMaster).order_by(LocationMaster.canonical_name.asc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_ward_profile(session: AsyncSession, ward_id: str) -> dict[str, Any] | None:
    stmt = select(WardProfile).where(WardProfile.ward_id == ward_id).limit(1)
    row = (await session.execute(stmt)).scalars().first()
    if row is None:
        return None
    return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Aggregation queries — return compact monthly/ranked summaries instead of
# raw time-series rows so the agent can reason over the data directly.
# ---------------------------------------------------------------------------


async def get_aqi_summary(session: AsyncSession, location_id: str) -> list[dict[str, Any]]:
    """Monthly AQI aggregates for a neighbourhood — up to 12 rows for a full year.

    Returns avg/min/max AQI and dominant category per calendar month.
    Use this instead of get_aqi_historical for annual trends or year-long summaries.
    """
    # Step 1: monthly aggregate stats
    aqi_month = func.date_trunc("month", AirQualityObservation.observed_at)
    agg_stmt = (
        select(
            aqi_month.label("month"),
            func.avg(AirQualityObservation.aqi_value).label("avg_aqi"),
            func.min(AirQualityObservation.aqi_value).label("min_aqi"),
            func.max(AirQualityObservation.aqi_value).label("max_aqi"),
            func.count().label("readings"),
        )
        .where(AirQualityObservation.location_id == location_id)
        .group_by(aqi_month)
        .order_by(aqi_month)
    )
    agg_rows = (await session.execute(agg_stmt)).all()

    # Step 2: category counts per month — pick dominant in Python
    # Reuse the same expression object so asyncpg prepared statements share one bind param
    cat_month = func.date_trunc("month", AirQualityObservation.observed_at)
    cat_stmt = (
        select(
            cat_month.label("month"),
            AirQualityObservation.aqi_category,
            func.count().label("cnt"),
        )
        .where(
            AirQualityObservation.location_id == location_id,
            AirQualityObservation.aqi_category.is_not(None),
        )
        .group_by(
            cat_month,
            AirQualityObservation.aqi_category,
        )
        .order_by(
            cat_month,
            func.count().desc(),
        )
    )
    cat_rows = (await session.execute(cat_stmt)).all()

    # Build month → dominant category map (first row per month has highest count)
    dom_map: dict[str, str] = {}
    for r in cat_rows:
        key = str(r.month)[:7]
        if key not in dom_map and r.aqi_category:
            dom_map[key] = r.aqi_category

    return [
        {
            "month": str(r.month)[:7],
            "location_id": location_id,
            "avg_aqi": round(float(r.avg_aqi)) if r.avg_aqi is not None else None,
            "min_aqi": r.min_aqi,
            "max_aqi": r.max_aqi,
            "dominant_category": dom_map.get(str(r.month)[:7]),
            "readings": r.readings,
        }
        for r in agg_rows
    ]


async def get_weather_summary(session: AsyncSession, location_id: str) -> list[dict[str, Any]]:
    """Monthly weather aggregates for a zone — up to 12 rows for a full year.

    Returns avg/max/min temperature, avg humidity, and total rainfall per month.
    Use this instead of get_weather_historical for annual or seasonal analysis.
    """
    zone_id = await _resolve_zone_id(session, location_id)
    month_expr = func.date_trunc("month", WeatherObservation.observed_at)
    month_col = month_expr.label("month")
    stmt = (
        select(
            month_col,
            func.avg(WeatherObservation.temperature_celsius).label("avg_temp_c"),
            func.max(WeatherObservation.temperature_celsius).label("max_temp_c"),
            func.min(WeatherObservation.temperature_celsius).label("min_temp_c"),
            func.avg(WeatherObservation.humidity_percent).label("avg_humidity_pct"),
            func.sum(WeatherObservation.rainfall_mm_hourly).label("total_rainfall_mm"),
            func.count().label("readings"),
        )
        .where(WeatherObservation.location_id == zone_id)
        .group_by(month_expr)
        .order_by(month_expr)
    )
    rows = (await session.execute(stmt)).all()

    def _r1(v: Any) -> float | None:
        return round(float(v), 1) if v is not None else None

    return [
        {
            "month": str(r.month)[:7],
            "zone_id": zone_id,
            "avg_temp_c": _r1(r.avg_temp_c),
            "max_temp_c": _r1(r.max_temp_c),
            "min_temp_c": _r1(r.min_temp_c),
            "avg_humidity_pct": _r1(r.avg_humidity_pct),
            "total_rainfall_mm": _r1(r.total_rainfall_mm),
            "readings": r.readings,
        }
        for r in rows
    ]


async def get_weather_extremes(
    session: AsyncSession,
    metric: str = "temperature_celsius",
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Top N extreme days across all zones ranked by the chosen metric.

    metric: 'temperature_celsius' (hottest days) or 'rainfall_mm_24hour' (wettest days).
    Returns date, zone_id, station_name, and the metric value.
    Use this to answer 'hottest day in 2023' or 'which area had the most rain'.
    """
    allowed_metrics = {"temperature_celsius", "rainfall_mm_24hour"}
    if metric not in allowed_metrics:
        metric = "temperature_celsius"

    obs_col = (
        WeatherObservation.temperature_celsius
        if metric == "temperature_celsius"
        else WeatherObservation.rainfall_mm_24hour
    )

    date_expr = func.date_trunc("day", WeatherObservation.observed_at)
    date_col = date_expr.label("date")
    agg_val = func.max(obs_col).label("value")

    stmt = (
        select(
            date_col,
            WeatherObservation.location_id,
            WeatherObservation.station_name,
            agg_val,
        )
        .where(obs_col.is_not(None))
        .group_by(date_expr, WeatherObservation.location_id, WeatherObservation.station_name)
        .order_by(agg_val.desc())
        .limit(top_n)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "date": str(r.date)[:10],
            "zone_id": r.location_id,
            "station_name": r.station_name,
            "metric": metric,
            "value": round(float(r.value), 1) if r.value is not None else None,
        }
        for r in rows
    ]
