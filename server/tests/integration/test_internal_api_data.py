from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from scripts import load_metrosense_dataset as loader

CSV_FIXTURES: dict[str, str] = {
    "air_quality_observations.csv": (
        "aq_obs_id,observed_at,ingested_at,station_id,station_name,station_type,source_name,"
        "location_id,ward_id,latitude,longitude,pm2_5,pm10,no2,so2,co,ozone,nh3,aqi_value,"
        "aqi_category,dominant_pollutant,data_quality_flag\n"
        "aq-1,2023-01-01 00:00:00,2023-01-01 00:01:00,aqst_ward_001,Hebbal CPCB Station,"
        "continuous,CPCB,Hebbal,ward_001,12.8527,77.7199,80.0,120.0,10.0,5.0,0.8,20.0,4.0,"
        "85,Satisfactory,PM10,good\n"
    ),
    "weather_observations.csv": (
        "observation_id,observed_at,ingested_at,station_id,station_name,station_type,source_name,"
        "location_id,ward_id,latitude,longitude,elevation_meters,temperature_celsius,"
        "humidity_percent,pressure_hpa,wind_speed_kmh,wind_gust_kmh,wind_direction_degrees,"
        "rainfall_mm_hourly,rainfall_mm_24hour,rainfall_intensity_mm_hr,visibility_km,"
        "data_quality_flag\n"
        "wx-1,2023-01-01 00:00:00,2023-01-01 00:01:00,wxst_zone_north,North Bangalore AWS,AWS,"
        "IMD,zone_north,,13.04,77.59,920,14.0,67.7,914.8,3.0,5.8,247,0.0,0.0,0.0,7.2,good\n"
    ),
    "flood_incidents.csv": (
        "incident_id,reported_at,resolved_at,location_id,ward_id,neighborhood_name,latitude,"
        "longitude,water_depth_cm,road_blocked_flag,vehicles_stranded_flag,property_damage_flag,"
        "pump_deployed_flag,source_type,severity,rainfall_mm_1h_at_time,rainfall_mm_3h_at_time,"
        "data_quality_flag\n"
        "flood-1,2023-06-01T02:00:00,2023-06-01T10:00:00,ward_001,ward_001,Hebbal,12.8961,"
        "77.6329,12,False,False,False,False,bbmp_log,low,5.47,8.46,good\n"
    ),
    "power_outage_events.csv": (
        "outage_id,event_id,started_at,restored_at,duration_minutes,location_id,ward_id,zone_name,"
        "feeder_id,feeder_name,substation_id,substation_name,outage_type,fault_type,cause_text,"
        "affected_customers,critical_load_affected_flag,wind_speed_kmh_at_time,wind_gust_kmh_at_time,"
        "rainfall_mm_1h_at_time,rainfall_mm_24h_at_time,source_name,data_quality_flag\n"
        "outage-1,evt_1,2023-01-01T14:21:00,2023-01-01T19:15:00,294,ward_001,ward_001,zone_north,"
        "fdr_003,Hebbal Feeder A,sub_003,Hebbal SS,unplanned,treefall,Treefall on feeder,2269,True,"
        "63.1,79.0,1.72,15.64,BESCOM,good\n"
    ),
    "traffic_segment_observations.csv": (
        "traffic_obs_id,observed_at,ingested_at,road_segment_id,road_name,corridor_name,location_id,"
        "ward_id,road_class,lanes_count,speed_limit_kmh,avg_speed_kmh,free_flow_speed_kmh,"
        "travel_time_minutes,free_flow_travel_time_minutes,delay_minutes,congestion_index,"
        "heavy_vehicle_share,waterlogging_flag,incident_type,incident_severity,rainfall_mm_1h_at_time,"
        "rainfall_mm_3h_at_time,source_name,data_quality_flag\n"
        "traffic-1,2023-01-01 00:00:00,2023-01-01 00:01:08,seg_orr,ORR,ORR,zone_north,,highway,6,"
        "60,48.0,60,12.0,10.0,2.0,0.3,0.2,False,,,0.0,0.0,TomTom,good\n"
    ),
    "lake_hydrology.csv": (
        "lake_obs_id,observed_at,ingested_at,lake_id,source_name,water_level_meters,fill_percentage,"
        "inflow_cusecs,outflow_cusecs,surplus_flow_cusecs,rainfall_last_1h_mm,rainfall_last_24h_mm,"
        "overflow_status,gate_status,number_of_gates_open,alert_level,encroachment_risk_flag,"
        "siltation_risk_flag,data_quality_flag\n"
        "lake-1,2023-01-01T00:00:00,2023-01-01T00:09:56,lake_001,KSNDMC,281.55,30.6,0.49,1.93,0.0,"
        "1.14,4.12,False,closed,0,Normal,True,True,good\n"
    ),
}


def _write_golden_fixture(tmp_path: Path) -> tuple[Path, Path]:
    dataset_dir = tmp_path / "DataSet_MetroSense"
    docs_dir = tmp_path / "Documents_Metrosense"
    dataset_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    for name, body in CSV_FIXTURES.items():
        (dataset_dir / name).write_text(body)

    index_payload = {
        "document_id": "test-doc",
        "wards_covered": ["Hebbal", "Bellandur", "Varthur"],
        "table_of_contents": [{"wards_mentioned": ["Hebbal", "Nagavara"]}],
    }
    (docs_dir / "test_index.json").write_text(json.dumps(index_payload))
    return dataset_dir, docs_dir


@pytest.mark.asyncio
async def test_internal_endpoints_return_seeded_data(
    client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_dir, docs_dir = _write_golden_fixture(tmp_path)
    monkeypatch.setattr(loader, "DATASET_DIR", dataset_dir)
    monkeypatch.setattr(loader, "DOCUMENTS_DIR", docs_dir)

    await loader.run_loader(replace=True)
    headers = {"X-Internal-Token": "test-internal-token"}

    weather_response = await client.get(
        "/internal/weather/current",
        params={"location_id": "zone_north"},
        headers=headers,
    )
    assert weather_response.status_code == 200
    weather_payload = weather_response.json()
    assert weather_payload
    assert weather_payload[0]["location_id"] == "zone_north"

    aqi_response = await client.get(
        "/internal/aqi/current",
        params={"location_id": "Hebbal"},
        headers=headers,
    )
    assert aqi_response.status_code == 200
    aqi_payload = aqi_response.json()
    assert aqi_payload
    assert aqi_payload[0]["location_id"] == "Hebbal"
