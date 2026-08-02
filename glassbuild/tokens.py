"""Loading and merging of the YAML token sources."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

MATERIALS: tuple[str, ...] = ("glass", "frosted-glass", "liquid-glass")
MODES: tuple[str, ...] = ("light", "dark")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing token file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_tokens(root: Path) -> dict[str, Any]:
    """Load every token file under ``root/tokens``."""
    tokens_dir = Path(root) / "tokens"
    return {
        "base": _read(tokens_dir / "base.yaml"),
        "materials": {name: _read(tokens_dir / f"{name}.yaml") for name in MATERIALS},
        "modes": {name: _read(tokens_dir / "modes" / f"{name}.yaml") for name in MODES},
    }


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)
    return target


def merge(*sources: dict[str, Any]) -> dict[str, Any]:
    """Merge token dicts left to right; later sources win. Inputs are not mutated."""
    result: dict[str, Any] = {}
    for source in sources:
        _deep_merge(result, source or {})
    return result
