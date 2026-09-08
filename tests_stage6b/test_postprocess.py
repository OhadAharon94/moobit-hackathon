import pandas as pd
import pytest

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance
from qera_stage6b.postprocess import (
    every_seed_passes_quality_gate,
    empirical_pvalue,
    matched_uniform_valid_batches,
    weighted_quantile,
    wilson_interval,
)


def test_d6_quality_gate_allows_each_seed_to_pass_either_metric() -> None:
    assert every_seed_passes_quality_gate(
        [0.01, 0.90, 0.02],
        [0.90, 0.01, 0.80],
    )


def test_d6_quality_gate_rejects_one_seed_failing_both_metrics() -> None:
    assert not every_seed_passes_quality_gate(
        [0.01, 0.90, 0.02],
        [0.90, 0.20, 0.80],
    )


def test_weighted_quantile_respects_multiplicities() -> None:
    assert weighted_quantile([1.0, 5.0], [3, 1], 0.5) == 1.0
    assert weighted_quantile([1.0, 5.0], [1, 3], 0.5) == 5.0


def test_wilson_interval_contains_observed_fraction() -> None:
    low, high = wilson_interval(42, 4096)
    assert low < 42 / 4096 < high
    with pytest.raises(ValueError):
        wilson_interval(1, 0)


def test_matched_valid_batches_are_deterministic_and_exact_size() -> None:
    evaluator = ScalingEvaluator(frozen_instance())
    first = matched_uniform_valid_batches(evaluator, 17, seed=99, batches=5)
    second = matched_uniform_valid_batches(evaluator, 17, seed=99, batches=5)
    assert first == second
    assert all(row["batch_size"] == 17 for row in first)
    assert all(0 <= row["joint_feasible_count"] <= 17 for row in first)


def test_empirical_pvalue_has_add_one_correction() -> None:
    assert empirical_pvalue([1.0, 2.0, 3.0], 0.0, lower_is_better=True) == 0.25
    assert empirical_pvalue([1.0, 2.0, 3.0], 4.0, lower_is_better=False) == 0.25
