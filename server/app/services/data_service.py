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


def _row_to_dict(row: Any) -> dict[str, Any]:
    mapper = inspect(type(row))
    payload: dict[str, Any] = {}
    for column in mapper.columns:
        payload[column.key] = getattr(row, column.key)
    return payload


async def get_weather_current(
    session: AsyncSession, location_id: str, limit: int = 1
) -> list[dict[str, Any]]:
    stmt = (
        select(WeatherObservation)
        .where(WeatherObservation.location_id == location_id)
        .order_by(WeatherObservation.observed_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_weather_historical(
    session: AsyncSession, location_id: str, hours: int = 24
) -> list[dict[str, Any]]:
    window_start = datetime.now(UTC) - timedelta(hours=hours)
    stmt = (
        select(WeatherObservation)
        .where(
            WeatherObservation.location_id == location_id,
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
    session: AsyncSession, location_id: str, days: int = 7
) -> list[dict[str, Any]]:
    window_start = datetime.now(UTC) - timedelta(days=days)
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
    stmt = (
        select(FloodIncident)
        .where(FloodIncident.location_id == location_id)
        .order_by(FloodIncident.reported_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(row) for row in rows]


async def get_power_outages(
    session: AsyncSession, location_id: str, window_days: int = 30
) -> list[dict[str, Any]]:
    window_start = datetime.now(UTC) - timedelta(days=window_days)
    stmt = (
        select(PowerOutageEvent)
        .where(
            PowerOutageEvent.location_id == location_id,
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
    stmt = (
        select(TrafficSegmentObservation)
        .where(TrafficSegmentObservation.location_id == location_id)
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
