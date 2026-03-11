from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AirQualityObservation,
    FloodIncident,
    LakeHydrology,
    PowerOutageEvent,
    TrafficSegmentObservation,
    WeatherObservation,
)


async def _domain_summary(
    session: AsyncSession,
    *,
    domain: str,
    stmt: Select[Any],
) -> dict[str, Any]:
    row = (await session.execute(stmt)).one()
    available_from, available_to, location_count = row
    has_data = available_to is not None
    return {
        "available_from": available_from.isoformat() if available_from else None,
        "available_to": available_to.isoformat() if available_to else None,
        "last_updated_at": available_to.isoformat() if available_to else None,
        "location_count": int(location_count or 0),
        "has_data": has_data,
        "dataset_note": (
            f"{domain} coverage: {available_from.isoformat()} to {available_to.isoformat()}."
            if has_data and available_from and available_to
            else f"No data currently available for {domain}."
        ),
    }


async def build_runtime_context(session: AsyncSession) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    domains = {
        "weather": await _domain_summary(
            session,
            domain="weather",
            stmt=select(
                func.min(WeatherObservation.observed_at),
                func.max(WeatherObservation.observed_at),
                func.count(func.distinct(WeatherObservation.location_id)),
            ),
        ),
        "aqi": await _domain_summary(
            session,
            domain="aqi",
            stmt=select(
                func.min(AirQualityObservation.observed_at),
                func.max(AirQualityObservation.observed_at),
                func.count(func.distinct(AirQualityObservation.location_id)),
            ),
        ),
        "lakes": await _domain_summary(
            session,
            domain="lakes",
            stmt=select(
                func.min(LakeHydrology.observed_at),
                func.max(LakeHydrology.observed_at),
                func.count(func.distinct(LakeHydrology.lake_id)),
            ),
        ),
        "floods": await _domain_summary(
            session,
            domain="floods",
            stmt=select(
                func.min(FloodIncident.reported_at),
                func.max(FloodIncident.reported_at),
                func.count(func.distinct(FloodIncident.location_id)),
            ),
        ),
        "outages": await _domain_summary(
            session,
            domain="outages",
            stmt=select(
                func.min(PowerOutageEvent.started_at),
                func.max(PowerOutageEvent.started_at),
                func.count(func.distinct(PowerOutageEvent.location_id)),
            ),
        ),
        "traffic": await _domain_summary(
            session,
            domain="traffic",
            stmt=select(
                func.min(TrafficSegmentObservation.observed_at),
                func.max(TrafficSegmentObservation.observed_at),
                func.count(func.distinct(TrafficSegmentObservation.corridor_name)),
            ),
        ),
    }
    return {"generated_at": generated_at, "domains": domains}
