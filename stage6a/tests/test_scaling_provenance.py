import json

import pytest

from scripts.process_scaling_qaoa import _resolve_recorded_path
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.provenance import (
    scaling_spec_sha256,
    sha256_file,
    validate_scaling_circuit_manifest,
)
from qera_scaling.qubo import build_energy_spec


def test_scaling_manifest_binds_program_and_objective(tmp_path) -> None:
    instance = generate_instance(5)
    weights = (1.0 / 3.0,) * 3
    spec = build_energy_spec(ScalingEvaluator(instance), weights, "cost")
    qprog = tmp_path / "circuit.qprog"
    qprog.write_text("test-program", encoding="utf-8")
    manifest = {
        "instance_id": instance.instance_id,
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": weights,
        "qaoa_depth": 1,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "synthesis_status": "SUCCESS",
        "qprog_sha256": sha256_file(qprog),
        "synthesis_spec_sha256": scaling_spec_sha256(spec, "cost", weights, 1),
    }
    path = tmp_path / "circuit.synthesis.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    validate_scaling_circuit_manifest(
        qprog, path, spec, instance.instance_id, weights
    )
    qprog.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="qprog hash"):
        validate_scaling_circuit_manifest(
            qprog, path, spec, instance.instance_id, weights
        )


def test_recorded_artifact_paths_are_portable(tmp_path) -> None:
    repository_root = tmp_path / "checkout"
    artifact = repository_root / "stage6a" / "circuit.qprog"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("program", encoding="utf-8")

    assert _resolve_recorded_path(
        "stage6a/circuit.qprog", repository_root, tmp_path / "fallback"
    ) == artifact
    assert _resolve_recorded_path(
        r"C:\old-checkout\stage6a\circuit.qprog", repository_root, artifact
    ) == artifact
