import json
from pathlib import Path

import pandas as pd
import pytest

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.postprocess import process_sample_frame
from qera_scaling.provenance import sha256_file
from qera_scaling.qubo import build_energy_spec

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = (1.0 / 3.0,) * 3


def assert_same(actual, expected) -> None:
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_same(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            assert_same(actual_item, expected_item)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, abs=1e-12)
    else:
        assert actual == expected


@pytest.mark.parametrize("D", [5, 6])
def test_saved_larger_quantum_evidence_reprocesses_without_drift(D: int) -> None:
    instance = generate_instance(D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    run_dir = (
        ROOT
        / "artifacts"
        / "scaling"
        / "qaoa"
        / f"{instance.instance_id}-p1-uniform-cost"
    )
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PROCESSED"
    assert manifest["samples_raw_sha256"] == sha256_file(run_dir / "samples_raw.csv")
    frames = {
        "qaoa": (run_dir / "samples_raw.csv", run_dir / "summary.json"),
        "uniform_random_bitstrings": (
            run_dir / "controls" / "uniform_random_bitstrings" / "samples_raw.csv",
            run_dir / "controls" / "uniform_random_bitstrings" / "summary.json",
        ),
        "uniform_random_valid_routes": (
            run_dir / "controls" / "uniform_random_valid_routes" / "samples_raw.csv",
            run_dir / "controls" / "uniform_random_valid_routes" / "summary.json",
        ),
    }
    for raw_path, summary_path in frames.values():
        _, actual = process_sample_frame(
            pd.read_csv(raw_path),
            evaluator,
            spec,
            WEIGHTS,
            declared_shots=4096,
        )
        expected = json.loads(summary_path.read_text(encoding="utf-8"))
        assert_same(actual, expected)
