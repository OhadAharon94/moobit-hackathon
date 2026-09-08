"""Versioned artifact serialization."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, MappingProxyType):
        return _jsonable(dict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def write_json(path: Path, payload: Any) -> Path:
    """Write deterministic, human-readable JSON and return the resolved path."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path.resolve()

