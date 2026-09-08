from math import isclose

from qera_scaling.audit import adaptive_audit, stable_weight_update


def test_independent_adaptive_update_invariants_and_trajectories() -> None:
    audit = adaptive_audit()
    assert audit["all_invariants_pass"]
    assert audit["expected_cost_trajectory_pass"]
    assert audit["expected_regret_trajectory_pass"]
    assert audit["cost_trajectory"] == [
        [1, 0, 2, 2],
        [1, 0, 2, 2],
        [0, 1, 1, 2],
    ]
    assert audit["regret_trajectory"] == [[0, 1, 1, 2]] * 3
    assert all(
        isclose(actual, expected, abs_tol=6e-4)
        for actual, expected in zip(
            audit["cost_weights"][1], (0.302, 0.291, 0.407), strict=True
        )
    )
    assert all(
        isclose(actual, expected, abs_tol=6e-4)
        for actual, expected in zip(
            audit["cost_weights"][2], (0.267, 0.247, 0.486), strict=True
        )
    )


def test_adaptive_clipping_and_zero_boost() -> None:
    assert stable_weight_update((0.5, 0.5), (-1.0, 2.0)) == stable_weight_update(
        (0.5, 0.5), (0.0, 1.0)
    )
    assert stable_weight_update((0.5, 0.5), (0.0, 0.0)) == (0.5, 0.5)
