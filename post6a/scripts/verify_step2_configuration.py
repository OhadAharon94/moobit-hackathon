"""Verify that Step 2 changes only the optimizer seed from frozen D=6."""

from __future__ import annotations

import json
from pathlib import Path

from holy_qow_post6a.common import artifact_root, sha256_file, write_json
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.provenance import validate_scaling_circuit_manifest
from qera_scaling.qubo import build_energy_spec

WEIGHTS = (1.0 / 3.0,) * 3
REPEAT_SEEDS = (6106, 6201, 6202, 6203, 6204)


def main() -> None:
    implementation = Path(__file__).resolve().parents[2]
    stage6a = implementation / "stage6a"
    original_run = (
        stage6a
        / "artifacts"
        / "scaling"
        / "qaoa"
        / "qera-d6-seed6106-p1-uniform-cost"
    )
    original_manifest_path = original_run / "manifest.json"
    qprog_path = (
        stage6a
        / "artifacts"
        / "scaling"
        / "circuits"
        / "qera-d6-seed6106-p1.qprog"
    )
    synthesis_manifest_path = qprog_path.with_suffix(".synthesis.json")
    original = json.loads(original_manifest_path.read_text(encoding="utf-8"))

    instance = generate_instance(6)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    circuit = validate_scaling_circuit_manifest(
        qprog_path,
        synthesis_manifest_path,
        spec,
        instance.instance_id,
        WEIGHTS,
    )

    expected = {
        "backend": "simulator",
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": list(WEIGHTS),
        "qaoa_depth": 1,
        "initial_parameters": {"params": [0.5, 0.5]},
        "optimizer_iteration_cap": 10,
        "optimizer_quantile": 1.0,
        "optimizer_shots": 512,
        "final_shots": 4096,
    }
    mismatches = {}
    for key, value in expected.items():
        if original.get(key) != value:
            mismatches[key] = {"expected": value, "recorded": original.get(key)}
    if original.get("qprog_sha256") != sha256_file(qprog_path):
        mismatches["qprog_sha256"] = {
            "expected": sha256_file(qprog_path),
            "recorded": original.get("qprog_sha256"),
        }
    if original.get("synthesis_spec_sha256") != circuit["synthesis_spec_sha256"]:
        mismatches["synthesis_spec_sha256"] = {
            "expected": circuit["synthesis_spec_sha256"],
            "recorded": original.get("synthesis_spec_sha256"),
        }
    if len(set(REPEAT_SEEDS)) != len(REPEAT_SEEDS):
        mismatches["repeat_seeds"] = "optimizer seeds are not unique"

    record = {
        "schema_version": "post6a-steps0-2-v1",
        "step": 2,
        "gate": "2A_configuration",
        "status": "PASS" if not mismatches else "FAIL",
        "principle": "all settings equal frozen Stage 6A D=6 except optimizer seed",
        "repeat_optimizer_seeds": list(REPEAT_SEEDS),
        "new_optimizer_seeds": list(REPEAT_SEEDS[1:]),
        "expected_configuration": expected,
        "mismatches": mismatches,
        "frozen_inputs": {
            "original_manifest_path": str(original_manifest_path.resolve()),
            "original_manifest_sha256": sha256_file(original_manifest_path),
            "qprog_path": str(qprog_path.resolve()),
            "qprog_sha256": sha256_file(qprog_path),
            "synthesis_manifest_path": str(synthesis_manifest_path.resolve()),
            "synthesis_manifest_sha256": sha256_file(synthesis_manifest_path),
            "synthesis_spec_sha256": circuit["synthesis_spec_sha256"],
        },
    }
    output = artifact_root() / "repeatability" / "configuration_gate.json"
    write_json(output, record)
    print(output.resolve())
    print(json.dumps(record, indent=2, sort_keys=True))
    if mismatches:
        raise SystemExit("Step 2 configuration gate failed")


if __name__ == "__main__":
    main()
