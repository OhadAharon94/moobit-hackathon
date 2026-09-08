"""Immutable artifact binding for the independent Stage 6B track."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def source_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    groups = (
        root / "qera",
        root / "stage6a" / "qera_scaling",
        root / "qera_stage6b",
    )
    files = sorted(path for group in groups for path in group.glob("*.py"))
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_qprog_manifest(
    qprog_path: Path,
    manifest_path: Path,
    *,
    circuit_kind: str,
) -> dict[str, Any]:
    if not qprog_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("bound Stage 6B qprog/manifest pair is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "circuit_kind",
        "synthesis_status",
        "qprog_sha256",
        "model_sha256",
        "source_sha256",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(f"incomplete Stage 6B synthesis manifest: {missing}")
    if manifest["synthesis_status"] != "SUCCESS":
        raise ValueError("cannot execute a circuit whose synthesis did not succeed")
    if manifest["circuit_kind"] != circuit_kind:
        raise ValueError("Stage 6B circuit kind mismatch")
    if manifest["qprog_sha256"] != sha256_file(qprog_path):
        raise ValueError("Stage 6B qprog hash mismatch")
    return manifest
