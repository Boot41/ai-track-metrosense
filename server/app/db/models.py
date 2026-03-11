from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LocationMaster(Base):
    __tablename__ = "location_master"

    location_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    ward_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ward_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    neighborhood_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pin_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WardProfile(Base):
    __tablename__ = "ward_profile"

    profile_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ward_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    population_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    elderly_population_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    children_population_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    slum_household_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    green_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    impervious_surface_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)


class LakeReference(Base):
    __tablename__ = "lake_reference"

    lake_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    lake_name: Mapped[str] = mapped_column(String(255), nullable=False)
    lake_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("location_master.location_id"), nullable=True, index=True
    )
    ward_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=True, index=True
    )
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    catchment_area_sqkm: Mapped[float | None] = mapped_column(Float, nullable=True)
    lake_area_sqkm: Mapped[float | None] = mapped_column(Float, nullable=True)
    full_tank_level_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_capacity_mcm: Mapped[float | None] = mapped_column(Float, nullable=True)
    number_of_gates: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)


class WeatherObservation(Base):
    __tablename__ = "weather_observation"

    observation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    station_id: Mapped[str] = mapped_column(String(128), nullable=False)
    station_name: Mapped[str] = mapped_column(String(255), nullable=False)
    station_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    ward_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=True, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gust_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_degrees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rainfall_mm_hourly: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm_24hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_intensity_mm_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    visibility_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_flag: Mapped[str] = mapped_column(String(32), nullable=False)


class AirQualityObservation(Base):
    __tablename__ = "air_quality_observation"

    aq_obs_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    station_id: Mapped[str] = mapped_column(String(128), nullable=False)
    station_name: Mapped[str] = mapped_column(String(255), nullable=False)
    station_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    ward_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pm2_5: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    ozone: Mapped[float | None] = mapped_column(Float, nullable=True)
    nh3: Mapped[float | None] = mapped_column(Float, nullable=True)
    aqi_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    aqi_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dominant_pollutant: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_quality_flag: Mapped[str] = mapped_column(String(32), nullable=False)


class LakeHydrology(Base):
    __tablename__ = "lake_hydrology"

    lake_obs_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lake_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("lake_reference.lake_id"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    water_level_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    inflow_cusecs: Mapped[float | None] = mapped_column(Float, nullable=True)
    outflow_cusecs: Mapped[float | None] = mapped_column(Float, nullable=True)
    surplus_flow_cusecs: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_last_1h_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_last_24h_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    overflow_status: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gate_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    number_of_gates_open: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alert_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    encroachment_risk_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    siltation_risk_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data_quality_flag: Mapped[str] = mapped_column(String(32), nullable=False)


class PowerOutageEvent(Base):
    __tablename__ = "power_outage_event"

    outage_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    ward_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=True, index=True
    )
    zone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feeder_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feeder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    substation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    substation_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    outage_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fault_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cause_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_customers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_load_affected_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    wind_speed_kmh_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gust_kmh_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm_1h_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm_24h_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_quality_flag: Mapped[str] = mapped_column(String(32), nullable=False)


class TrafficSegmentObservation(Base):
    __tablename__ = "traffic_segment_observation"

    traffic_obs_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    road_segment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    road_name: Mapped[str] = mapped_column(String(255), nullable=False)
    corridor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    ward_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=True, index=True
    )
    latitude_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lanes_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speed_limit_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_flow_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    travel_time_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_flow_travel_time_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    delay_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    congestion_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    heavy_vehicle_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    waterlogging_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    incident_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    incident_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rainfall_mm_1h_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm_3h_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_quality_flag: Mapped[str] = mapped_column(String(32), nullable=False)


class FloodIncident(Base):
    __tablename__ = "flood_incident"

    incident_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("location_master.location_id"), nullable=False, index=True
    )
    ward_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("location_master.location_id"), nullable=True, index=True
    )
    neighborhood_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_depth_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_blocked_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    vehicles_stranded_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    property_damage_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pump_deployed_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rainfall_mm_1h_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    rainfall_mm_3h_at_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_flag: Mapped[str] = mapped_column(String(32), nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    user_role: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    turn_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("sessions.session_id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    agents_invoked: Mapped[list[str]] = mapped_column(JSON, default=list)
    response_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cited_documents: Mapped[list[str]] = mapped_column(JSON, default=list)
    cited_records: Mapped[list[str]] = mapped_column(JSON, default=list)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "overall_confidence >= 0 AND overall_confidence <= 1", name="ck_audit_conf"
        ),
    )

    log_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("sessions.session_id"), nullable=True, index=True
    )
    turn_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("conversation_history.turn_id"), nullable=True, index=True
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent_classified: Mapped[str | None] = mapped_column(String(128), nullable=True)
    agents_invoked: Mapped[list[str]] = mapped_column(JSON, default=list)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_freshness_lag_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stale_sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    error_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )


__all__ = [
    "AirQualityObservation",
    "AuditLog",
    "ConversationHistory",
    "FloodIncident",
    "LakeHydrology",
    "LakeReference",
    "LocationMaster",
    "PowerOutageEvent",
    "Session",
    "TrafficSegmentObservation",
    "User",
    "WardProfile",
    "WeatherObservation",
]
