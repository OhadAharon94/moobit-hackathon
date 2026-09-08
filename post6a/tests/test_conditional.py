from __future__ import annotations

import math

from holy_qow_post6a.conditional import (
    conditional_record,
    load_reprocessed_qaoa,
    matched_valid_batches,
)


def test_saved_d6_probability_factorization() -> None:
    processed, summary = load_reprocessed_qaoa(6)
    record = conditional_record(6, processed, summary)
    assert record["one_hot_count"] == 25
    assert math.isclose(
        record["p_near_optimal"],
        record["p_one_hot"] * record["p_near_optimal_given_onehot"],
        abs_tol=1e-15,
    )


def test_matched_valid_batches_have_exact_requested_size_and_are_deterministic() -> None:
    first = matched_valid_batches(6, 7, batches=5, seed=12345)
    second = matched_valid_batches(6, 7, batches=5, seed=12345)
    assert first == second
    assert all(row["batch_size"] == 7 for row in first)
    assert all(0 <= row["joint_feasible_count"] <= 7 for row in first)
