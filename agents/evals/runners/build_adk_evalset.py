from __future__ import annotations

import argparse
from pathlib import Path
import sys

AGENTS_DIR = Path(__file__).resolve().parents[2]
if str(AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(AGENTS_DIR))

from evals.lib.adk import write_generated_files
from evals.lib.catalog import dump_json, load_catalog
from evals.lib.models import MetroSenseEvalCatalog, schema_output_path


def _write_schema(repo_root: Path) -> Path:
    path = schema_output_path(repo_root)
    dump_json(path, MetroSenseEvalCatalog.model_json_schema())
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MetroSense ADK eval artifacts.")
    parser.add_argument(
        "--catalog",
        action="append",
        required=True,
        help="Path to a canonical eval catalog JSON file. Can be passed multiple times.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    schema_path = _write_schema(repo_root)
    print(f"Wrote schema: {schema_path}")

    for catalog_path_str in args.catalog:
        catalog_path = (repo_root / catalog_path_str).resolve()
        catalog = load_catalog(catalog_path)
        eval_set_path, eval_config_path = write_generated_files(repo_root, catalog)
        print(f"Wrote eval set: {eval_set_path}")
        print(f"Wrote eval config: {eval_config_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
