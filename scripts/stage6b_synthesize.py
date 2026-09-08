"""Synthesize Stage 6B circuits only; never execute them."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from classiq import create_model, get_transpiled_circuit_metrics, synthesize

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance, generate_instance
from qera_scaling.provenance import scaling_spec_sha256
from qera_scaling.qubo import build_energy_spec
from qera_stage6b.model import (
    build_constrained_qaoa_main,
    build_initial_state_main,
    build_single_demand_mixer_main,
)
from qera_stage6b.provenance import sha256_file, source_sha256


WEIGHTS = (1.0 / 3.0,) * 3
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


def _metrics(metrics: Any) -> dict[str, Any]:
    operations = dict(getattr(metrics, "count_ops", {}) or {})
    return {
        "synthesized_qubits": getattr(metrics, "width", None),
        "depth": getattr(metrics, "depth", None),
        "gate_count": sum(int(value) for value in operations.values()),
        "two_qubit_gate_count": sum(
            int(value)
            for gate, value in operations.items()
            if gate.lower() in TWO_QUBIT_GATES
        ),
        "count_ops": operations,
    }


def _synthesize_one(
    model: Callable,
    output_stem: Path,
    base_manifest: dict[str, Any],
) -> dict[str, Any]:
    qmod_path = output_stem.with_suffix(".qmod.json")
    qprog_path = output_stem.with_suffix(".qprog")
    manifest_path = output_stem.with_suffix(".synthesis.json")
    collisions = [path for path in (qmod_path, qprog_path, manifest_path) if path.exists()]
    if collisions:
        raise FileExistsError(f"refusing to overwrite Stage 6B evidence: {collisions}")
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    qmod = create_model(model)
    qmod_path.write_text(qmod, encoding="utf-8")
    started = perf_counter()
    common = {
        **base_manifest,
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "classiq_sdk_version": version("classiq"),
        "qmod_path": str(qmod_path.resolve()),
        "model_sha256": sha256_file(qmod_path),
    }
    try:
        qprog = synthesize(model)
        qprog_path.write_text(qprog.model_dump_json(indent=2), encoding="utf-8")
        manifest = {
            **common,
            "synthesis_status": "SUCCESS",
            "synthesis_runtime_seconds": perf_counter() - started,
            "qprog_path": str(qprog_path.resolve()),
            "qprog_sha256": sha256_file(qprog_path),
            "failure_type": None,
            "failure_message": None,
            **_metrics(get_transpiled_circuit_metrics(qprog)),
        }
    except Exception as error:
        manifest = {
            **common,
            "synthesis_status": "FAILED",
            "synthesis_runtime_seconds": perf_counter() - started,
            "qprog_path": None,
            "qprog_sha256": None,
            "failure_type": type(error).__name__,
            "failure_message": str(error),
            "synthesized_qubits": None,
            "depth": None,
            "gate_count": None,
            "two_qubit_gate_count": None,
            "count_ops": None,
        }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(manifest_path.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["synthesis_status"] != "SUCCESS":
        raise RuntimeError(
            f"Stage 6B synthesis failed: {manifest['failure_type']}: "
            f"{manifest['failure_message']}"
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("a1", "d4", "d6"), required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifact_root = root / "artifacts" / "stage6b"
    source_hash = source_sha256(root)

    if args.phase == "a1":
        _synthesize_one(
            build_initial_state_main(1),
            artifact_root / "stateprep" / "single_demand",
            {
                "circuit_kind": "single-demand-dicke-stateprep",
                "D": 1,
                "K": 3,
                "qaoa_depth": 0,
                "scenario_weights": None,
                "source_sha256": source_hash,
            },
        )
        for route in range(3):
            _synthesize_one(
                build_single_demand_mixer_main(route),
                artifact_root / "mixer_validation" / f"basis-{route}",
                {
                    "circuit_kind": f"single-demand-xy-mixer-basis-{route}",
                    "initial_route": route,
                    "D": 1,
                    "K": 3,
                    "qaoa_depth": 0,
                    "scenario_weights": None,
                    "mixer_pair_order": [[0, 1], [1, 2], [0, 2]],
                    "pair_unitary": "RXX(2*beta) then RYY(2*beta)",
                    "source_sha256": source_hash,
                },
            )
        return

    D = 4 if args.phase == "d4" else 6
    instance = frozen_instance() if D == 4 else generate_instance(D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    common = {
        "D": D,
        "K": instance.paths_per_demand,
        "instance_id": instance.instance_id,
        "instance_seed": instance.seed,
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": WEIGHTS,
        "qaoa_depth": 1,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "synthesis_spec_sha256": scaling_spec_sha256(spec, "cost", WEIGHTS, 1),
        "source_sha256": source_hash,
    }
    if D == 4:
        _synthesize_one(
            build_initial_state_main(D),
            artifact_root / "stateprep" / "d4_initial",
            {
                **common,
                "circuit_kind": "d4-independent-dicke-stateprep",
                "qaoa_depth": 0,
            },
        )
    _synthesize_one(
        build_constrained_qaoa_main(spec, D, depth=1),
        artifact_root / f"d{D}" / "constrained_p1",
        {
            **common,
            "circuit_kind": f"d{D}-constrained-qaoa-p1",
            "mixer_pair_order": [[0, 1], [1, 2], [0, 2]],
            "pair_unitary": "RXX(2*beta) then RYY(2*beta)",
            "one_hot_penalty_retained": True,
        },
    )


if __name__ == "__main__":
    main()
