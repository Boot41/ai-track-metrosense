from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, settings
from app.core.config import Settings
from app.services import data_service

router = APIRouter(prefix="/internal", tags=["internal"])


def require_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
    app_settings: Settings = Depends(settings),
) -> None:
    expected = app_settings.agent_internal_token.strip()
    if not expected or x_internal_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )


@router.get(
    "/weather/current",
    dependencies=[Depends(require_internal_token)],
)
async def weather_current(
    location_id: str,
    limit: int = Query(default=1, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_weather_current(session, location_id=location_id, limit=limit)


@router.get(
    "/weather/historical",
    dependencies=[Depends(require_internal_token)],
)
async def weather_historical(
    location_id: str,
    hours: int = Query(default=720, ge=1, le=8760),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_weather_historical(session, location_id=location_id, hours=hours)


@router.get(
    "/aqi/current",
    dependencies=[Depends(require_internal_token)],
)
async def aqi_current(
    location_id: str,
    limit: int = Query(default=1, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_aqi_current(session, location_id=location_id, limit=limit)


@router.get(
    "/aqi/historical",
    dependencies=[Depends(require_internal_token)],
)
async def aqi_historical(
    location_id: str,
    days: int = Query(default=365, ge=1, le=3650),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_aqi_historical(session, location_id=location_id, days=days)


@router.get(
    "/lakes",
    dependencies=[Depends(require_internal_token)],
)
async def lakes(
    lake_id: str,
    limit: int = Query(default=5, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_lake_hydrology(session, lake_id=lake_id, limit=limit)


@router.get(
    "/floods",
    dependencies=[Depends(require_internal_token)],
)
async def floods(
    location_id: str,
    limit: int = Query(default=20, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_flood_incidents(session, location_id=location_id, limit=limit)


@router.get(
    "/outages",
    dependencies=[Depends(require_internal_token)],
)
async def outages(
    location_id: str,
    window_days: int = Query(default=365, ge=1, le=3650),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_power_outages(
        session, location_id=location_id, window_days=window_days
    )


@router.get(
    "/traffic/current",
    dependencies=[Depends(require_internal_token)],
)
async def traffic_current(
    location_id: str,
    limit: int = Query(default=5, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_traffic_current(session, location_id=location_id, limit=limit)


@router.get(
    "/traffic/corridor",
    dependencies=[Depends(require_internal_token)],
)
async def traffic_corridor(
    corridor_name: str,
    limit: int = Query(default=20, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.get_traffic_corridor(
        session, corridor_name=corridor_name, limit=limit
    )


@router.get(
    "/locations/resolve",
    dependencies=[Depends(require_internal_token)],
)
async def locations_resolve(
    name: str,
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.resolve_location(session, name=name)


@router.get(
    "/locations",
    dependencies=[Depends(require_internal_token)],
)
async def locations(
    limit: int = Query(default=200, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[dict[str, Any]]:
    return await data_service.list_locations(session, limit=limit)


@router.get(
    "/ward/profile",
    dependencies=[Depends(require_internal_token)],
)
async def ward_profile(
    ward_id: str,
    session: AsyncSession = Depends(db_session),
) -> dict[str, Any] | None:
    return await data_service.get_ward_profile(session, ward_id=ward_id)
