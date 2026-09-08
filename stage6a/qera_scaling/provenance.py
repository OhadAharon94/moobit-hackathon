"""Stage 6A artifact hashing and circuit/objective binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from qera_scaling.qubo import ScalingEnergySpec


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_sha256(implementation_root: Path, stage6a_root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted((implementation_root / "qera").glob("*.py")) + sorted(
        (stage6a_root / "qera_scaling").glob("*.py")
    )
    for path in files:
        digest.update(path.resolve().as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def scaling_spec_payload(
    spec: ScalingEnergySpec,
    objective_mode: str,
    scenario_weights: Sequence[float],
    qaoa_depth: int,
) -> dict:
    return {
        "objective_mode": objective_mode,
        "energy_mode": "base",
        "scenario_weights": [float(value) for value in scenario_weights],
        "qaoa_depth": int(qaoa_depth),
        "M": float(spec.qubo.one_hot_penalty),
        "phase_offset": float(spec.phase_offset),
        "phase_scale": float(spec.phase_scale),
        "range_mode": spec.range_mode,
        "qubo": {
            "offset": float(spec.qubo.offset),
            "linear": [float(value) for value in spec.qubo.linear],
            "quadratic": [
                [left, right, float(value)]
                for (left, right), value in sorted(spec.qubo.quadratic.items())
            ],
        },
    }


def scaling_spec_sha256(
    spec: ScalingEnergySpec,
    objective_mode: str,
    scenario_weights: Sequence[float],
    qaoa_depth: int,
) -> str:
    encoded = json.dumps(
        scaling_spec_payload(spec, objective_mode, scenario_weights, qaoa_depth),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_scaling_circuit_manifest(
    qprog_path: Path,
    manifest_path: Path,
    spec: ScalingEnergySpec,
    instance_id: str,
    scenario_weights: Sequence[float],
) -> dict:
    if not qprog_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("bound Stage 6A qprog/manifest pair is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "instance_id",
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
        raise ValueError(f"incomplete Stage 6A synthesis manifest: {missing}")
    if manifest["synthesis_status"] != "SUCCESS":
        raise ValueError("cannot execute a circuit whose synthesis did not succeed")
    if manifest["instance_id"] != instance_id:
        raise ValueError("circuit instance does not match execution instance")
    if manifest["objective_mode"] != "cost" or manifest["energy_mode"] != "base":
        raise ValueError("circuit objective/energy mode mismatch")
    if int(manifest["qaoa_depth"]) != 1:
        raise ValueError("Stage 6A core requires p=1")
    actual_weights = tuple(float(value) for value in manifest["scenario_weights"])
    expected_weights = tuple(float(value) for value in scenario_weights)
    if len(actual_weights) != len(expected_weights) or any(
        abs(actual - expected) > 1e-10
        for actual, expected in zip(actual_weights, expected_weights, strict=True)
    ):
        raise ValueError("circuit scenario weights do not match execution request")
    for key, expected in (
        ("M", spec.qubo.one_hot_penalty),
        ("phase_offset", spec.phase_offset),
        ("phase_scale", spec.phase_scale),
    ):
        if abs(float(manifest[key]) - float(expected)) > 1e-10:
            raise ValueError(f"circuit {key} does not match execution request")
    if manifest["qprog_sha256"] != sha256_file(qprog_path):
        raise ValueError("Stage 6A qprog hash mismatch")
    expected_hash = scaling_spec_sha256(spec, "cost", expected_weights, 1)
    if manifest["synthesis_spec_sha256"] != expected_hash:
        raise ValueError("Stage 6A synthesis specification hash mismatch")
    return manifest
