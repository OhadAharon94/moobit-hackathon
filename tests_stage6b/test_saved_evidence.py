import json
from pathlib import Path

import pandas as pd
import pytest

from qera.config import FINAL_SHOTS
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance
from qera_scaling.qubo import build_energy_spec
from qera_stage6b.postprocess import WEIGHTS, process_saved_frame
from qera_stage6b.provenance import sha256_file


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "stage6b"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_single_demand_correctness_evidence_passes() -> None:
    stateprep = _json(ARTIFACTS / "stage6b_stateprep_validation.json")
    mixer = _json(ARTIFACTS / "stage6b_mixer_preservation.json")
    assert stateprep["status"] == "PASS"
    assert set(stateprep["statevector"]["nonzero_probabilities"]) == {
        "001",
        "010",
        "100",
    }
    assert stateprep["sampled"]["invalid_shots"] == 0
    assert mixer["status"] == "PASS"
    assert mixer["trial_count"] == 12
    assert mixer["total_sampled_shots"] == 49152
    assert all(trial["sampled"]["invalid_shots"] == 0 for trial in mixer["trials"])
    assert all(
        trial["statevector"]["invalid_hamming_weight_probability"] <= 1e-10
        for trial in mixer["trials"]
    )


def test_d4_preoptimization_correctness_gates_pass() -> None:
    gates = _json(ARTIFACTS / "d4" / "d4_correctness_gates.json")
    assert gates["status"] == "PASS"
    assert gates["initial_distribution"]["statevector_valid_support"] == 81
    assert gates["initial_distribution"]["sample_invalid_shots"] == 0
    assert gates["initial_distribution"]["bit_ordering_verified"] is True
    assert gates["unoptimized_full_ansatz"]["sample_invalid_shots"] == 0
    assert gates["cost_compatibility"]["assignments_checked"] == 81
    assert gates["cost_compatibility"]["pairwise_ordering_mismatches"] == 0


@pytest.mark.parametrize("seed", [6601, 6602, 6603])
def test_saved_d4_quantum_runs_reprocess_without_drift(seed: int) -> None:
    run = ARTIFACTS / "d4" / "runs" / f"seed-{seed}"
    manifest = _json(run / "manifest.json")
    assert manifest["status"] == "RAW_SAMPLE_SAVED"
    assert manifest["samples_raw_sha256"] == sha256_file(run / "samples_raw.csv")
    evaluator = ScalingEvaluator(frozen_instance())
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    _, _, metrics = process_saved_frame(
        pd.read_csv(run / "samples_raw.csv"),
        evaluator,
        spec,
        FINAL_SHOTS,
    )
    expected = _json(run / "summary.json")["distribution_metrics"]
    for key, value in expected.items():
        if isinstance(value, float):
            assert metrics[key] == pytest.approx(value, abs=1e-12)
        else:
            assert metrics[key] == value
    assert metrics["one_hot_probability"] == 1.0
    assert metrics["total_shots"] == FINAL_SHOTS


def test_resource_comparison_matches_bound_qprogs() -> None:
    resources = _json(ARTIFACTS / "tables" / "circuit_resource_analysis.json")
    assert resources["x_mixer"]["width"] == 12
    assert resources["constraint_preserving_xy"]["width"] == 12
    assert resources["x_mixer"]["depth"] == 65
    assert resources["constraint_preserving_xy"]["depth"] == 101
    assert resources["x_mixer"]["two_qubit_gate_count"] == 84
    assert resources["constraint_preserving_xy"]["two_qubit_gate_count"] == 164


def test_d6_gate_is_frozen_no_go_and_no_d6_quantum_program_exists() -> None:
    gate = _json(ARTIFACTS / "d6" / "gate_decision.json")
    assert gate["status"] == "NOT_ATTEMPTED"
    assert gate["gate_passed"] is False
    assert gate["decision"] == "STOP_AT_D4"
    assert not (ARTIFACTS / "d6" / "constrained_p1.qprog").exists()


def test_frozen_x_mixer_qprog_remains_unchanged() -> None:
    assert sha256_file(ROOT / "artifacts" / "circuits" / "uniform_cost_p1.qprog") == (
        "9d6b2fd05b1757a070c756c407d64a06e877030ba4397303c6bae9310bbcfd7e"
    )
