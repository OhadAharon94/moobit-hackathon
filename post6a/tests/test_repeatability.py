from __future__ import annotations

import math

from holy_qow_post6a.repeatability import (
    REPEAT_SEEDS,
    aggregate_optimizer_seed_variability,
    wilson_interval,
)


def test_repeat_seed_set_preserves_original_and_adds_four_unique_seeds() -> None:
    assert REPEAT_SEEDS[0] == 6106
    assert len(REPEAT_SEEDS) == 5
    assert len(set(REPEAT_SEEDS)) == 5


def test_wilson_interval_contains_observed_fraction() -> None:
    low, high = wilson_interval(8, 25)
    assert low is not None and high is not None
    assert low < 8 / 25 < high


def test_wilson_interval_handles_zero_denominator_explicitly() -> None:
    assert wilson_interval(0, 0) == (None, None)


def test_seed_variability_is_not_shot_pooled() -> None:
    records = [
        {"method": "qaoa", "x": value} for value in (0.0, 0.5, 1.0)
    ] + [{"method": "control", "x": 99.0}]
    result = aggregate_optimizer_seed_variability(records, ("x",))[0]
    assert result["variability_source"] == "optimizer_seed"
    assert result["seed_count"] == 3
    assert math.isclose(result["mean"], 0.5)
