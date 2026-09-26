"""Load and merge LegacyLift configuration.

Defaults live in the package's bundled ``legacylift.yaml``. A project may
have its own ``legacylift.yaml`` (created/updated by ``legacylift ingest``)
whose values are merged on top, key by key, recursively.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "legacylift.yaml"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_default_config() -> dict[str, Any]:
    if _DEFAULT_CONFIG_PATH.exists():
        with open(_DEFAULT_CONFIG_PATH, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    return {}


def load_config(project_path: Path, explicit_config: Path | None = None) -> dict[str, Any]:
    """Load defaults, then merge a project-local legacylift.yaml if present."""
    cfg = load_default_config()
    candidate = explicit_config or (project_path / "legacylift.yaml")
    if candidate.exists():
        with open(candidate, encoding="utf-8") as fh:
            project_cfg = yaml.safe_load(fh) or {}
        cfg = _deep_merge(cfg, project_cfg)
    return cfg


def save_config(cfg: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
