"""add metrosense climate schema

Revision ID: 20260311_0002
Revises: 20260310_0001
Create Date: 2026-03-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260311_0002"
down_revision = "20260310_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "location_master",
        sa.Column("location_id", sa.String(length=128), primary_key=True),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("location_type", sa.String(length=32), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("ward_id", sa.String(length=64), nullable=True),
        sa.Column("ward_name", sa.String(length=255), nullable=True),
        sa.Column("zone_name", sa.String(length=64), nullable=True),
        sa.Column("neighborhood_name", sa.String(length=255), nullable=True),
        sa.Column("pin_code", sa.String(length=16), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=128), primary_key=True),
        sa.Column("user_role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_turns", sa.Integer(), nullable=False),
        sa.Column("active_flag", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "lake_reference",
        sa.Column("lake_id", sa.String(length=128), primary_key=True),
        sa.Column("lake_name", sa.String(length=255), nullable=False),
        sa.Column("lake_type", sa.String(length=32), nullable=True),
        sa.Column("location_id", sa.String(length=128), nullable=True),
        sa.Column("ward_id", sa.String(length=64), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("catchment_area_sqkm", sa.Float(), nullable=True),
        sa.Column("lake_area_sqkm", sa.Float(), nullable=True),
        sa.Column("full_tank_level_meters", sa.Float(), nullable=True),
        sa.Column("max_capacity_mcm", sa.Float(), nullable=True),
        sa.Column("number_of_gates", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location_master.location_id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index(
        "ix_lake_reference_location_id",
        "lake_reference",
        ["location_id"],
        unique=False,
    )
    op.create_index("ix_lake_reference_ward_id", "lake_reference", ["ward_id"], unique=False)

    op.create_table(
        "ward_profile",
        sa.Column("profile_id", sa.String(length=128), primary_key=True),
        sa.Column("ward_id", sa.String(length=64), nullable=False),
        sa.Column("population_density", sa.Float(), nullable=True),
        sa.Column("elderly_population_pct", sa.Float(), nullable=True),
        sa.Column("children_population_pct", sa.Float(), nullable=True),
        sa.Column("slum_household_count", sa.Integer(), nullable=True),
        sa.Column("green_cover_pct", sa.Float(), nullable=True),
        sa.Column("impervious_surface_pct", sa.Float(), nullable=True),
        sa.Column("data_year", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index("ix_ward_profile_ward_id", "ward_profile", ["ward_id"], unique=False)

    op.create_table(
        "air_quality_observation",
        sa.Column("aq_obs_id", sa.String(length=128), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("station_id", sa.String(length=128), nullable=False),
        sa.Column("station_name", sa.String(length=255), nullable=False),
        sa.Column("station_type", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("location_id", sa.String(length=128), nullable=False),
        sa.Column("ward_id", sa.String(length=64), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("pm2_5", sa.Float(), nullable=True),
        sa.Column("pm10", sa.Float(), nullable=True),
        sa.Column("no2", sa.Float(), nullable=True),
        sa.Column("so2", sa.Float(), nullable=True),
        sa.Column("co", sa.Float(), nullable=True),
        sa.Column("ozone", sa.Float(), nullable=True),
        sa.Column("nh3", sa.Float(), nullable=True),
        sa.Column("aqi_value", sa.Integer(), nullable=True),
        sa.Column("aqi_category", sa.String(length=32), nullable=True),
        sa.Column("dominant_pollutant", sa.String(length=32), nullable=True),
        sa.Column("data_quality_flag", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location_master.location_id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index(
        "ix_air_quality_observation_location_id",
        "air_quality_observation",
        ["location_id"],
    )
    op.create_index(
        "ix_air_quality_observation_observed_at",
        "air_quality_observation",
        ["observed_at"],
    )
    op.create_index("ix_air_quality_observation_ward_id", "air_quality_observation", ["ward_id"])

    op.create_table(
        "weather_observation",
        sa.Column("observation_id", sa.String(length=128), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("station_id", sa.String(length=128), nullable=False),
        sa.Column("station_name", sa.String(length=255), nullable=False),
        sa.Column("station_type", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("location_id", sa.String(length=128), nullable=False),
        sa.Column("ward_id", sa.String(length=64), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("elevation_meters", sa.Float(), nullable=True),
        sa.Column("temperature_celsius", sa.Float(), nullable=True),
        sa.Column("humidity_percent", sa.Float(), nullable=True),
        sa.Column("pressure_hpa", sa.Float(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=True),
        sa.Column("wind_gust_kmh", sa.Float(), nullable=True),
        sa.Column("wind_direction_degrees", sa.Integer(), nullable=True),
        sa.Column("rainfall_mm_hourly", sa.Float(), nullable=True),
        sa.Column("rainfall_mm_24hour", sa.Float(), nullable=True),
        sa.Column("rainfall_intensity_mm_hr", sa.Float(), nullable=True),
        sa.Column("visibility_km", sa.Float(), nullable=True),
        sa.Column("data_quality_flag", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location_master.location_id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index("ix_weather_observation_location_id", "weather_observation", ["location_id"])
    op.create_index("ix_weather_observation_observed_at", "weather_observation", ["observed_at"])
    op.create_index("ix_weather_observation_ward_id", "weather_observation", ["ward_id"])

    op.create_table(
        "flood_incident",
        sa.Column("incident_id", sa.String(length=128), primary_key=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_id", sa.String(length=128), nullable=False),
        sa.Column("ward_id", sa.String(length=64), nullable=True),
        sa.Column("neighborhood_name", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("water_depth_cm", sa.Float(), nullable=True),
        sa.Column("road_blocked_flag", sa.Boolean(), nullable=True),
        sa.Column("vehicles_stranded_flag", sa.Boolean(), nullable=True),
        sa.Column("property_damage_flag", sa.Boolean(), nullable=True),
        sa.Column("pump_deployed_flag", sa.Boolean(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("rainfall_mm_1h_at_time", sa.Float(), nullable=True),
        sa.Column("rainfall_mm_3h_at_time", sa.Float(), nullable=True),
        sa.Column("data_quality_flag", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location_master.location_id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index("ix_flood_incident_location_id", "flood_incident", ["location_id"])
    op.create_index("ix_flood_incident_reported_at", "flood_incident", ["reported_at"])
    op.create_index("ix_flood_incident_ward_id", "flood_incident", ["ward_id"])

    op.create_table(
        "power_outage_event",
        sa.Column("outage_id", sa.String(length=128), primary_key=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("location_id", sa.String(length=128), nullable=False),
        sa.Column("ward_id", sa.String(length=64), nullable=True),
        sa.Column("zone_name", sa.String(length=64), nullable=True),
        sa.Column("feeder_id", sa.String(length=128), nullable=True),
        sa.Column("feeder_name", sa.String(length=255), nullable=True),
        sa.Column("substation_id", sa.String(length=128), nullable=True),
        sa.Column("substation_name", sa.String(length=255), nullable=True),
        sa.Column("outage_type", sa.String(length=32), nullable=True),
        sa.Column("fault_type", sa.String(length=32), nullable=True),
        sa.Column("cause_text", sa.Text(), nullable=True),
        sa.Column("affected_customers", sa.Integer(), nullable=True),
        sa.Column("critical_load_affected_flag", sa.Boolean(), nullable=True),
        sa.Column("wind_speed_kmh_at_time", sa.Float(), nullable=True),
        sa.Column("wind_gust_kmh_at_time", sa.Float(), nullable=True),
        sa.Column("rainfall_mm_1h_at_time", sa.Float(), nullable=True),
        sa.Column("rainfall_mm_24h_at_time", sa.Float(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("data_quality_flag", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location_master.location_id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index("ix_power_outage_event_event_id", "power_outage_event", ["event_id"])
    op.create_index("ix_power_outage_event_location_id", "power_outage_event", ["location_id"])
    op.create_index("ix_power_outage_event_started_at", "power_outage_event", ["started_at"])
    op.create_index("ix_power_outage_event_ward_id", "power_outage_event", ["ward_id"])

    op.create_table(
        "traffic_segment_observation",
        sa.Column("traffic_obs_id", sa.String(length=128), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("road_segment_id", sa.String(length=128), nullable=False),
        sa.Column("road_name", sa.String(length=255), nullable=False),
        sa.Column("corridor_name", sa.String(length=255), nullable=True),
        sa.Column("location_id", sa.String(length=128), nullable=False),
        sa.Column("ward_id", sa.String(length=64), nullable=True),
        sa.Column("latitude_start", sa.Float(), nullable=True),
        sa.Column("longitude_start", sa.Float(), nullable=True),
        sa.Column("latitude_end", sa.Float(), nullable=True),
        sa.Column("longitude_end", sa.Float(), nullable=True),
        sa.Column("road_class", sa.String(length=32), nullable=True),
        sa.Column("lanes_count", sa.Integer(), nullable=True),
        sa.Column("speed_limit_kmh", sa.Float(), nullable=True),
        sa.Column("avg_speed_kmh", sa.Float(), nullable=True),
        sa.Column("free_flow_speed_kmh", sa.Float(), nullable=True),
        sa.Column("travel_time_minutes", sa.Float(), nullable=True),
        sa.Column("free_flow_travel_time_minutes", sa.Float(), nullable=True),
        sa.Column("delay_minutes", sa.Float(), nullable=True),
        sa.Column("congestion_index", sa.Float(), nullable=True),
        sa.Column("heavy_vehicle_share", sa.Float(), nullable=True),
        sa.Column("waterlogging_flag", sa.Boolean(), nullable=True),
        sa.Column("incident_type", sa.String(length=64), nullable=True),
        sa.Column("incident_severity", sa.String(length=32), nullable=True),
        sa.Column("rainfall_mm_1h_at_time", sa.Float(), nullable=True),
        sa.Column("rainfall_mm_3h_at_time", sa.Float(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("data_quality_flag", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["location_master.location_id"]),
        sa.ForeignKeyConstraint(["ward_id"], ["location_master.location_id"]),
    )
    op.create_index(
        "ix_traffic_segment_observation_location_id", "traffic_segment_observation", ["location_id"]
    )
    op.create_index(
        "ix_traffic_segment_observation_observed_at", "traffic_segment_observation", ["observed_at"]
    )
    op.create_index(
        "ix_traffic_segment_observation_road_segment_id",
        "traffic_segment_observation",
        ["road_segment_id"],
    )
    op.create_index(
        "ix_traffic_segment_observation_ward_id",
        "traffic_segment_observation",
        ["ward_id"],
    )

    op.create_table(
        "lake_hydrology",
        sa.Column("lake_obs_id", sa.String(length=128), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lake_id", sa.String(length=128), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("water_level_meters", sa.Float(), nullable=True),
        sa.Column("fill_percentage", sa.Float(), nullable=True),
        sa.Column("inflow_cusecs", sa.Float(), nullable=True),
        sa.Column("outflow_cusecs", sa.Float(), nullable=True),
        sa.Column("surplus_flow_cusecs", sa.Float(), nullable=True),
        sa.Column("rainfall_last_1h_mm", sa.Float(), nullable=True),
        sa.Column("rainfall_last_24h_mm", sa.Float(), nullable=True),
        sa.Column("overflow_status", sa.Boolean(), nullable=True),
        sa.Column("gate_status", sa.String(length=32), nullable=True),
        sa.Column("number_of_gates_open", sa.Integer(), nullable=True),
        sa.Column("alert_level", sa.String(length=32), nullable=True),
        sa.Column("encroachment_risk_flag", sa.Boolean(), nullable=True),
        sa.Column("siltation_risk_flag", sa.Boolean(), nullable=True),
        sa.Column("data_quality_flag", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["lake_id"], ["lake_reference.lake_id"]),
    )
    op.create_index("ix_lake_hydrology_lake_id", "lake_hydrology", ["lake_id"])
    op.create_index("ix_lake_hydrology_observed_at", "lake_hydrology", ["observed_at"])

    op.create_table(
        "conversation_history",
        sa.Column("turn_id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("agents_invoked", sa.JSON(), nullable=False),
        sa.Column("response_mode", sa.String(length=16), nullable=True),
        sa.Column("cited_documents", sa.JSON(), nullable=False),
        sa.Column("cited_records", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
    )
    op.create_index("ix_conversation_history_session_id", "conversation_history", ["session_id"])
    op.create_index("ix_conversation_history_timestamp", "conversation_history", ["timestamp"])

    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("turn_id", sa.String(length=128), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("intent_classified", sa.String(length=128), nullable=True),
        sa.Column("agents_invoked", sa.JSON(), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("data_freshness_lag_seconds", sa.Integer(), nullable=True),
        sa.Column("stale_sources", sa.JSON(), nullable=False),
        sa.Column("error_flag", sa.Boolean(), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "overall_confidence >= 0 AND overall_confidence <= 1",
            name="ck_audit_conf",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"]),
        sa.ForeignKeyConstraint(["turn_id"], ["conversation_history.turn_id"]),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_session_id", "audit_log", ["session_id"])
    op.create_index("ix_audit_log_turn_id", "audit_log", ["turn_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_turn_id", table_name="audit_log")
    op.drop_index("ix_audit_log_session_id", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_conversation_history_timestamp", table_name="conversation_history")
    op.drop_index("ix_conversation_history_session_id", table_name="conversation_history")
    op.drop_table("conversation_history")

    op.drop_index("ix_lake_hydrology_observed_at", table_name="lake_hydrology")
    op.drop_index("ix_lake_hydrology_lake_id", table_name="lake_hydrology")
    op.drop_table("lake_hydrology")

    op.drop_index(
        "ix_traffic_segment_observation_ward_id",
        table_name="traffic_segment_observation",
    )
    op.drop_index(
        "ix_traffic_segment_observation_road_segment_id", table_name="traffic_segment_observation"
    )
    op.drop_index(
        "ix_traffic_segment_observation_observed_at",
        table_name="traffic_segment_observation",
    )
    op.drop_index(
        "ix_traffic_segment_observation_location_id",
        table_name="traffic_segment_observation",
    )
    op.drop_table("traffic_segment_observation")

    op.drop_index("ix_power_outage_event_ward_id", table_name="power_outage_event")
    op.drop_index("ix_power_outage_event_started_at", table_name="power_outage_event")
    op.drop_index("ix_power_outage_event_location_id", table_name="power_outage_event")
    op.drop_index("ix_power_outage_event_event_id", table_name="power_outage_event")
    op.drop_table("power_outage_event")

    op.drop_index("ix_flood_incident_ward_id", table_name="flood_incident")
    op.drop_index("ix_flood_incident_reported_at", table_name="flood_incident")
    op.drop_index("ix_flood_incident_location_id", table_name="flood_incident")
    op.drop_table("flood_incident")

    op.drop_index("ix_weather_observation_ward_id", table_name="weather_observation")
    op.drop_index("ix_weather_observation_observed_at", table_name="weather_observation")
    op.drop_index("ix_weather_observation_location_id", table_name="weather_observation")
    op.drop_table("weather_observation")

    op.drop_index("ix_air_quality_observation_ward_id", table_name="air_quality_observation")
    op.drop_index("ix_air_quality_observation_observed_at", table_name="air_quality_observation")
    op.drop_index("ix_air_quality_observation_location_id", table_name="air_quality_observation")
    op.drop_table("air_quality_observation")

    op.drop_index("ix_ward_profile_ward_id", table_name="ward_profile")
    op.drop_table("ward_profile")

    op.drop_index("ix_lake_reference_ward_id", table_name="lake_reference")
    op.drop_index("ix_lake_reference_location_id", table_name="lake_reference")
    op.drop_table("lake_reference")

    op.drop_table("sessions")
    op.drop_table("location_master")
