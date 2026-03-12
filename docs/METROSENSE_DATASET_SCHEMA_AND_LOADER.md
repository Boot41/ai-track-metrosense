# MetroSense Dataset Schema and Loader

This documents the backend changes implemented for loading MetroSense golden data into PostgreSQL.

## What was implemented

- Added MetroSense database schema (12 architecture tables) while keeping existing auth `users` table.
- Added a new Alembic migration to create the schema.
- Added an idempotent loader that reads directly from CSV files in:
  - `server/DataSet_MetroSense/`
- Added validation and test coverage for:
  - idempotent reload,
  - rollback on mid-run failure,
  - reference normalization diagnostics.

## Files changed

- `server/app/db/models.py`
  - Added models for:
    - `location_master`
    - `ward_profile`
    - `lake_reference`
    - `weather_observation`
    - `air_quality_observation`
    - `lake_hydrology`
    - `power_outage_event`
    - `traffic_segment_observation`
    - `flood_incident`
    - `sessions`
    - `conversation_history`
    - `audit_log`
  - Existing `User` model remains.

- `server/alembic/versions/20260311_0002_metrosense_schema.py`
  - Creates all MetroSense tables, foreign keys, and core indexes.

- `server/scripts/load_metrosense_dataset.py`
  - CSV-driven loader (direct reads via `csv.DictReader`).
  - Parses source timestamps as IST (`Asia/Kolkata`) into timezone-aware DB values.
  - Performs replace-style loading (`TRUNCATE` + reload) inside a single transaction.
  - Normalizes references (`location_master`, `ward_profile`, `lake_reference`) before fact loads.
  - Adds explicit validation for location/lake coverage before commit.
  - Supports failure simulation: `--simulate-failure-after-truncate`.

- `server/tests/integration/test_metrosense_dataset_loader.py`
  - Tests:
    - replace + idempotent behavior
    - rollback safety on simulated crash
    - clear diagnostics for missing normalized location IDs

- `server/scripts/__init__.py`
  - Added so `scripts` is importable in tests.

## How to run

From `server/`:

```bash
uv run alembic upgrade head
uv run python scripts/load_metrosense_dataset.py --replace
```

## Loader behavior

- Reads directly from the golden CSV files in `server/DataSet_MetroSense/`.
- Loads reference tables first, then fact/event tables.
- Uses one transaction; if anything fails, the whole load is rolled back.
- `--replace` is required to avoid partial/unclear state semantics.

## Verification commands used

From `server/`:

```bash
uv run ruff check app/db/models.py scripts/load_metrosense_dataset.py tests/integration/test_metrosense_dataset_loader.py
uv run mypy scripts/load_metrosense_dataset.py app/db/models.py tests/integration/test_metrosense_dataset_loader.py
uv run pytest tests/integration/test_metrosense_dataset_loader.py -q
uv run pytest tests/unit -q
uv run pytest tests/integration -q
```
