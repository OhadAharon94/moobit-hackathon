"""Synthesize one bound Stage 6A p=1 circuit; never execute it."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from importlib.metadata import version
import json
from pathlib import Path
import re
from time import perf_counter
from typing import Any

from classiq import get_transpiled_circuit_metrics, synthesize

from qera_scaling.classiq_model import build_qaoa_main
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.provenance import (
    scaling_spec_sha256,
    sha256_file,
    source_sha256,
)
from qera_scaling.qubo import build_energy_spec

TWO_QUBIT_GATES = {
    "cx",
    "cy",
    "cz",
    "swap",
    "rxx",
    "ryy",
    "rzz",
    "rzx",
    "ecr",
    "crx",
    "cry",
    "crz",
    "csx",
    "cu",
    "cp",
    "ch",
}


def _metrics(metrics: Any) -> dict:
    operations = dict(getattr(metrics, "count_ops", {}) or {})
    return {
        "synthesized_qubits": getattr(metrics, "width", None),
        "depth": getattr(metrics, "depth", None),
        "gate_count": sum(int(value) for value in operations.values()),
        "two_qubit_gate_count": sum(
            int(value) for gate, value in operations.items() if gate.lower() in TWO_QUBIT_GATES
        ),
        "count_ops": operations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, choices=(5, 6, 8), required=True)
    parser.add_argument(
        "--artifact-tag",
        default=None,
        help="Optional safe suffix for a new immutable synthesis attempt.",
    )
    args = parser.parse_args()
    if args.artifact_tag is not None and not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", args.artifact_tag
    ):
        raise ValueError("artifact tag contains unsafe characters")
    stage6a_root = Path(__file__).resolve().parents[1]
    implementation_root = stage6a_root.parent
    instance = generate_instance(args.D)
    weights = (1.0 / 3.0,) * 3
    spec = build_energy_spec(ScalingEvaluator(instance), weights, "cost")
    stem = f"{instance.instance_id}-p1"
    if args.artifact_tag:
        stem = f"{stem}-{args.artifact_tag}"
    circuit_dir = stage6a_root / "artifacts" / "scaling" / "circuits"
    circuit_dir.mkdir(parents=True, exist_ok=True)
    qprog_path = circuit_dir / f"{stem}.qprog"
    manifest_path = circuit_dir / f"{stem}.synthesis.json"
    if qprog_path.exists() or manifest_path.exists():
        raise FileExistsError(
            "refusing to overwrite existing synthesis evidence; use a new --artifact-tag"
        )
    started = perf_counter()
    base_manifest = {
        "schema_version": "stage6a-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "classiq_sdk_version": version("classiq"),
        "instance_id": instance.instance_id,
        "seed": instance.seed,
        "D": instance.demand_count,
        "K": instance.paths_per_demand,
        "S": instance.scenario_count,
        "logical_bits": instance.variable_count,
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": weights,
        "qaoa_depth": 1,
        "artifact_tag": args.artifact_tag,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "energy_range_mode": spec.range_mode,
        "source_sha256": source_sha256(implementation_root, stage6a_root),
        "instance_sha256": sha256_file(
            stage6a_root
            / "artifacts"
            / "scaling"
            / "instances"
            / f"{instance.instance_id}.json"
        ),
        "synthesis_spec_sha256": scaling_spec_sha256(spec, "cost", weights, 1),
    }
    try:
        qprog = synthesize(build_qaoa_main(spec, depth=1))
        runtime = perf_counter() - started
        qprog_path.write_text(qprog.model_dump_json(indent=2), encoding="utf-8")
        manifest = {
            **base_manifest,
            "synthesis_status": "SUCCESS",
            "synthesis_runtime_seconds": runtime,
            "warning": (
                "D=8 phase scaling uses guaranteed coefficient bounds, not exhaustive raw-state extrema."
                if spec.range_mode != "exhaustive"
                else None
            ),
            "qprog_path": str(qprog_path.resolve()),
            "qprog_sha256": sha256_file(qprog_path),
            **_metrics(get_transpiled_circuit_metrics(qprog)),
        }
    except Exception as error:
        manifest = {
            **base_manifest,
            "synthesis_status": "FAILED",
            "synthesis_runtime_seconds": perf_counter() - started,
            "warning": f"{type(error).__name__}: {error}",
            "qprog_path": None,
            "qprog_sha256": None,
            "synthesized_qubits": None,
            "depth": None,
            "gate_count": None,
            "two_qubit_gate_count": None,
            "count_ops": None,
        }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(manifest_path.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["synthesis_status"] != "SUCCESS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
