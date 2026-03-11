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
