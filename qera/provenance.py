"""Cryptographic binding between a QAOA program and its scientific metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from qera.energy import EnergySpec

FLOAT_TOLERANCE = 1e-10


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree_sha256(root: Path) -> str:
    """Hash relative names and contents of all source modules deterministically."""

    digest = hashlib.sha256()
    for path in sorted((root / "qera").glob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def synthesis_spec_payload(
    spec: EnergySpec,
    objective_mode: str,
    scenario_weights: Sequence[float],
    qaoa_depth: int,
) -> dict[str, Any]:
    return {
        "objective_mode": objective_mode,
        "energy_mode": spec.energy_mode,
        "scenario_weights": [float(value) for value in scenario_weights],
        "qaoa_depth": int(qaoa_depth),
        "M": float(spec.qubo.one_hot_penalty),
        "Lambda": spec.capacity_penalty,
        "phase_offset": float(spec.phase_offset),
        "phase_scale": float(spec.phase_scale),
        "qubo": {
            "offset": float(spec.qubo.offset),
            "linear": [float(value) for value in spec.qubo.linear],
            "quadratic": [
                [left, right, float(value)]
                for (left, right), value in sorted(spec.qubo.quadratic.items())
            ],
        },
    }


def synthesis_spec_sha256(
    spec: EnergySpec,
    objective_mode: str,
    scenario_weights: Sequence[float],
    qaoa_depth: int,
) -> str:
    payload = synthesis_spec_payload(
        spec, objective_mode, scenario_weights, qaoa_depth
    )
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def circuit_binding(
    qprog_path: Path,
    implementation_root: Path,
    spec: EnergySpec,
    objective_mode: str,
    scenario_weights: Sequence[float],
    qaoa_depth: int,
) -> dict[str, str]:
    return {
        "qprog_sha256": sha256_file(qprog_path),
        "synthesis_spec_sha256": synthesis_spec_sha256(
            spec, objective_mode, scenario_weights, qaoa_depth
        ),
        "code_sha256": source_tree_sha256(implementation_root),
        "config_sha256": sha256_file(implementation_root / "qera" / "config.py"),
    }


def synthesis_manifest_path(qprog_path: Path) -> Path:
    return qprog_path.with_suffix(".synthesis.json")


def require_explicit_qprog_for_nonuniform_weights(
    scenario_weights: Sequence[float],
    uniform_weights: Sequence[float],
    supplied_qprog: Path | None,
) -> None:
    """Prevent an implicit uniform circuit from serving a weighted objective."""

    actual = tuple(float(value) for value in scenario_weights)
    expected = tuple(float(value) for value in uniform_weights)
    if len(actual) != len(expected):
        raise ValueError("scenario weight vector has the wrong length")
    is_uniform = all(
        abs(value - reference) <= FLOAT_TOLERANCE
        for value, reference in zip(actual, expected, strict=True)
    )
    if supplied_qprog is None and not is_uniform:
        raise ValueError(
            "nonuniform --weights require an explicit --qprog and bound synthesis manifest"
        )


def _require_close(manifest: dict[str, Any], key: str, expected: float) -> None:
    if key not in manifest or abs(float(manifest[key]) - expected) > FLOAT_TOLERANCE:
        raise ValueError(
            f"circuit manifest {key} mismatch: expected {expected!r}, "
            f"found {manifest.get(key)!r}"
        )


def validate_circuit_manifest(
    qprog_path: Path,
    manifest_path: Path,
    spec: EnergySpec,
    objective_mode: str,
    scenario_weights: Sequence[float],
    qaoa_depth: int,
) -> dict[str, Any]:
    """Reject any program not cryptographically bound to the requested objective."""

    if not qprog_path.is_file():
        raise FileNotFoundError(f"missing synthesized qprog: {qprog_path}")
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"missing synthesis manifest: {manifest_path}; re-synthesize this circuit"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "objective_mode",
        "energy_mode",
        "scenario_weights",
        "qaoa_depth",
        "M",
        "phase_offset",
        "phase_scale",
        "qprog_sha256",
        "synthesis_spec_sha256",
    }
    missing = sorted(required.difference(manifest))
    if missing:
        raise ValueError(
            f"legacy or incomplete synthesis manifest is not executable; "
            f"missing {missing}. Re-synthesize to create a bound manifest."
        )
    if manifest["objective_mode"] != objective_mode:
        raise ValueError("circuit objective mode does not match execution request")
    if manifest["energy_mode"] != spec.energy_mode:
        raise ValueError("circuit energy mode does not match execution request")
    if int(manifest["qaoa_depth"]) != qaoa_depth:
        raise ValueError("circuit QAOA depth does not match execution request")
    actual_weights = tuple(float(value) for value in manifest["scenario_weights"])
    expected_weights = tuple(float(value) for value in scenario_weights)
    if len(actual_weights) != len(expected_weights) or any(
        abs(actual - expected) > FLOAT_TOLERANCE
        for actual, expected in zip(actual_weights, expected_weights, strict=True)
    ):
        raise ValueError("circuit scenario weights do not match execution request")
    _require_close(manifest, "M", float(spec.qubo.one_hot_penalty))
    _require_close(manifest, "phase_offset", float(spec.phase_offset))
    _require_close(manifest, "phase_scale", float(spec.phase_scale))
    actual_qprog_hash = sha256_file(qprog_path)
    if manifest["qprog_sha256"] != actual_qprog_hash:
        raise ValueError("qprog hash does not match its synthesis manifest")
    expected_spec_hash = synthesis_spec_sha256(
        spec, objective_mode, expected_weights, qaoa_depth
    )
    if manifest["synthesis_spec_sha256"] != expected_spec_hash:
        raise ValueError("circuit energy specification hash does not match request")
    return manifest
