import json
from math import isclose
from pathlib import Path

import pandas as pd

from qera.classiq_solver import process_sample_frame
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator


RUN_NAMES = (
    "uniform_cost_p1_smoke",
    "uniform_regret_p1_smoke",
    "adaptive_cost_t1",
    "adaptive_cost_t2",
)


def _assert_same(actual, expected) -> None:
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            _assert_same(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_same(actual_item, expected_item)
    elif isinstance(expected, float):
        assert isclose(float(actual), expected, abs_tol=1e-10)
    else:
        assert actual == expected


def test_all_saved_quantum_evidence_reprocesses_without_drift() -> None:
    root = Path(__file__).resolve().parents[1] / "artifacts" / "runs"
    for run_name in RUN_NAMES:
        run = root / run_name
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        expected = json.loads((run / "summary.json").read_text(encoding="utf-8"))
        weights = tuple(manifest["scenario_weights"])
        evaluator = Evaluator()
        spec = build_energy_spec(
            evaluator, weights, manifest["objective_mode"], manifest["energy_mode"]
        )
        _, actual = process_sample_frame(
            pd.read_csv(run / "samples_raw.csv"),
            evaluator,
            spec,
            weights,
            manifest["objective_mode"],
            declared_shots=manifest["final_shots"],
        )
        assert actual["total_shots"] == 4096
        _assert_same(actual, expected)
