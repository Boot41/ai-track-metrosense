  ### MetroSense Golden Dataset → Postgres (12-table architecture + idempotent load)

  #### Summary

  - Implement the full 12-table architecture from UrbanClimate_AI_Architecture.md, while keeping existing auth users
    unchanged.
  - Convert and load all CSVs in server/DataSet_MetroSense/ into normalized Postgres tables with explicit foreign
    keys and domain checks.
  - Add a manual, idempotent loader command that replaces dataset-driven tables on each run so DB state always
    matches the golden CSVs.
  - Treat source timestamps as Asia/Kolkata local time and store as timestamptz.

  #### Implementation Changes

  - Schema + migration
      - Add architecture tables: location_master, ward_profile, lake_reference, weather_observation,
        air_quality_observation, lake_hydrology, power_outage_event, traffic_segment_observation, flood_incident,
        sessions, conversation_history, audit_log.
      - Keep users table intact; new migration depends on current head.
      - Add PK/FK/indexes for high-volume query paths (observed_at, ward_id, location_id, lake_id, road_segment_id,
        started_at, reported_at).
      - Use nullable columns where golden CSVs don’t provide values (notably traffic segment geometry fields,
        weather/traffic ward gaps), but keep table purpose and constraints explicit.
      - Add controlled checks/enums for categorical fields (severity, outage/fault type, gate/alert status, etc.)
        aligned to observed golden values.
  - Reference normalization from golden data
      - Build location_master from deduplicated CSV location_id/ward_id plus document index ward/location names; keep
        aliases as array.
      - Build lake_reference from known lake_id set in hydrology + canonical names derived from golden document
        indexes.
      - Seed ward_profile minimally (ward identity + source metadata) with nullable profile metrics until
        quantitative source is added.
  - Loader command (idempotent replace)
      - Add server script (manual command) to run: begin transaction → set timezone Asia/Kolkata → truncate dataset-
        driven tables in FK-safe order → load references → load fact/event tables from CSV → validate row counts/FK
        integrity → commit.
      - Use bulk loading (COPY-style path) for large CSVs (air_quality, weather, traffic) to keep runtime practical.
      - Keep operational tables (sessions, conversation_history, audit_log) schema-only (no initial data load from
        CSV).
  - Developer workflow/interface
      - Expose one repeatable command, e.g. uv run python scripts/load_metrosense_dataset.py --replace.
      - Document run order in backend README: alembic upgrade head then loader command.

  #### Test Plan

  - Migration test: new tables/constraints/indexes exist; downgrade/upgrade cycle works.
  - Loader integration test: row counts exactly match CSV files for all six dataset tables.
  - Integrity test: all FK references resolve (location_id, ward_id, lake_id) and categorical checks pass.
  - Timestamp test: sampled rows are interpreted as IST input and stored correctly as timestamptz.
  - Idempotency test: running loader twice yields identical counts and no duplicates.

  #### Assumptions / Defaults Locked

  - Full 12 architecture tables are added now; existing users remains.
  - Golden data source is server/DataSet_MetroSense/ + normalization hints from server/Documents_Metrosense/.
  - Reload policy is replace (truncate + reload), not upsert.
  - No fabricated derived risk scores or document-derived computed tables are stored in Postgres.







  ### MetroSense Golden Dataset → Postgres (Revised with failure-safety + normalization validation)

  #### Summary

  - Implement full 12-table architecture from UrbanClimate_AI_Architecture.md, keep existing users table unchanged.
  - Load all golden CSVs into normalized Postgres tables via a manual idempotent loader (replace semantics).
  - Parse source timestamps as IST and store in timestamptz.
  - Add explicit pre-commit validation for location integrity and an explicit rollback-safety test for mid-run
    failures.

  #### Implementation Changes

  - Schema + migration
      - Add: location_master, ward_profile, lake_reference, weather_observation, air_quality_observation,
        lake_hydrology, power_outage_event, traffic_segment_observation, flood_incident, sessions,
        conversation_history, audit_log.
      - Keep users as-is; create additive Alembic revision from current head.
      - Add PK/FK/indexes for major query keys (observed_at, started_at, reported_at, ward_id, location_id, lake_id,
        road_segment_id) and checks for categorical domains.
  - Reference normalization + hard validation
      - Build canonical location_master/lake_reference/minimal ward_profile from deduped CSV entities, enriched by
        Documents_Metrosense indexes.
      - Add a loader validation stage before commit that:
          - verifies all fact-table location_id values map to canonical location_master,
          - verifies all ward_id/lake_id references resolve,
          - fails with a clear diagnostic report listing unknown or mismatched IDs (instead of only FK error text).
  - Loader workflow
      - Add uv run python scripts/load_metrosense_dataset.py --replace.
      - Single DB transaction for truncate→load→validate→commit.
      - On any error, explicit rollback and non-zero exit; no partial state persisted.
      - Keep operational tables schema-only (no CSV seed data).

  #### Test Plan

  - Migration test: all new tables, constraints, and indexes created; upgrade/downgrade succeeds.
  - Loader count test: loaded row counts match all 6 CSVs exactly.
  - Integrity test: FK resolution + categorical constraints pass.
  - Partial-failure recovery test: seed known pre-run state, inject simulated loader failure after truncate/before
    full load, assert final DB state equals pre-run snapshot (proves transaction rollback, not empty DB).
  - Validation diagnostics test: intentionally inject unknown/dirty location_id in fixture and assert loader fails
    with actionable mismatch report.
  - Timestamp test: sampled rows confirm IST interpretation into timestamptz.
  - Idempotency test: repeated runs produce identical dataset tables without duplicates.

  #### Assumptions / Defaults

  - Full 12 architecture tables are in scope now; users remains.
  - Golden source remains server/DataSet_MetroSense/ with normalization hints from server/Documents_Metrosense/.
  - Reload strategy is truncate+reload (replace), not upsert.
  - No derived risk scores or document-derived computed tables are stored in Postgres.
