import json
from pathlib import Path

import pytest

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.provenance import (
    circuit_binding,
    require_explicit_qprog_for_nonuniform_weights,
    validate_circuit_manifest,
)


def _bound_files(tmp_path):
    root = tmp_path / "implementation"
    (root / "qera").mkdir(parents=True)
    (root / "qera" / "config.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "qera" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    qprog = tmp_path / "circuit.qprog"
    qprog.write_text('{"program": "test"}', encoding="utf-8")
    spec = build_energy_spec(Evaluator(), INITIAL_SCENARIO_WEIGHTS, "cost")
    manifest = {
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": list(INITIAL_SCENARIO_WEIGHTS),
        "qaoa_depth": 1,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        **circuit_binding(
            qprog, root, spec, "cost", INITIAL_SCENARIO_WEIGHTS, 1
        ),
    }
    manifest_path = tmp_path / "circuit.synthesis.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return qprog, manifest_path, spec


def test_matching_circuit_manifest_is_accepted(tmp_path) -> None:
    qprog, manifest, spec = _bound_files(tmp_path)
    validated = validate_circuit_manifest(
        qprog, manifest, spec, "cost", INITIAL_SCENARIO_WEIGHTS, 1
    )
    assert validated["objective_mode"] == "cost"


@pytest.mark.parametrize(
    "field,value",
    [
        ("objective_mode", "regret"),
        ("energy_mode", "aligned"),
        ("scenario_weights", [0.2, 0.3, 0.5]),
        ("qaoa_depth", 2),
        ("M", 99.0),
        ("phase_scale", 99.0),
    ],
)
def test_scientific_manifest_mismatch_is_rejected(tmp_path, field, value) -> None:
    qprog, manifest_path, spec = _bound_files(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        validate_circuit_manifest(
            qprog, manifest_path, spec, "cost", INITIAL_SCENARIO_WEIGHTS, 1
        )


def test_tampered_qprog_is_rejected(tmp_path) -> None:
    qprog, manifest, spec = _bound_files(tmp_path)
    qprog.write_text('{"program": "tampered"}', encoding="utf-8")
    with pytest.raises(ValueError, match="qprog hash"):
        validate_circuit_manifest(
            qprog, manifest, spec, "cost", INITIAL_SCENARIO_WEIGHTS, 1
        )


def test_legacy_unbound_manifest_is_rejected(tmp_path) -> None:
    qprog, manifest_path, spec = _bound_files(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("qprog_sha256")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="legacy or incomplete"):
        validate_circuit_manifest(
            qprog, manifest_path, spec, "cost", INITIAL_SCENARIO_WEIGHTS, 1
        )


def test_nonuniform_weights_cannot_implicitly_select_uniform_circuit() -> None:
    with pytest.raises(ValueError, match="explicit --qprog"):
        require_explicit_qprog_for_nonuniform_weights(
            (0.2, 0.3, 0.5), INITIAL_SCENARIO_WEIGHTS, None
        )
    require_explicit_qprog_for_nonuniform_weights(
        (0.2, 0.3, 0.5), INITIAL_SCENARIO_WEIGHTS, Path("weighted.qprog")
    )
