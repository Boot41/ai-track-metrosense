from __future__ import annotations

import json
from pathlib import Path

from .models import MetroSenseEvalCatalog


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_catalog(path: Path) -> MetroSenseEvalCatalog:
    return MetroSenseEvalCatalog.model_validate_json(path.read_text(encoding="utf-8"))


def load_catalogs(paths: list[Path]) -> list[MetroSenseEvalCatalog]:
    return [load_catalog(path) for path in paths]


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
