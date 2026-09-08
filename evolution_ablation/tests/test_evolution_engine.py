from __future__ import annotations

from math import exp, isclose

from holy_qow_evolution.audit import global_update_audit, verify_run
from holy_qow_evolution.engine import ScenarioOracle, run_adaptive_exact, update_weights
from holy_qow_evolution.scenarios import original_training_pool


def test_weight_update_matches_declared_formula() -> None:
    weights = (0.2, 0.3, 0.5)
    regrets = (-1.0, 0.25, 2.0)
    clipped, pre, mixed = update_weights(weights, regrets, eta=0.5, rho=0.25)
    assert clipped == (0.0, 0.25, 1.0)
    raw = tuple(w * exp(0.5 * r) for w, r in zip(weights, clipped, strict=True))
    expected_pre = tuple(value / sum(raw) for value in raw)
    expected_mixed = tuple(0.75 * value + 0.25 / 3.0 for value in expected_pre)
    assert all(isclose(a, b, abs_tol=1e-15) for a, b in zip(pre, expected_pre, strict=True))
    assert all(isclose(a, b, abs_tol=1e-15) for a, b in zip(mixed, expected_mixed, strict=True))


def test_eta_zero_and_rho_contraction() -> None:
    weights = (0.2, 0.3, 0.5)
    _, pre, unchanged = update_weights(weights, (0.1, 0.5, 0.9), eta=0.0, rho=0.0)
    assert pre == weights
    assert unchanged == weights
    _, before, after = update_weights(weights, (0.1, 0.5, 0.9), eta=1.0, rho=0.4)
    uniform = 1.0 / 3.0
    before_distance = sum(abs(value - uniform) for value in before)
    after_distance = sum(abs(value - uniform) for value in after)
    assert isclose(after_distance, 0.6 * before_distance, abs_tol=1e-15)


def test_original_exact_trajectory_and_all_ties() -> None:
    scenarios = original_training_pool()
    run = run_adaptive_exact(scenarios, eta=1.0, iterations=3, rho=0.0)
    assert tuple(step.assignment for step in run.steps) == (
        (1, 0, 2, 2),
        (1, 0, 2, 2),
        (0, 1, 1, 2),
    )
    assert all(verify_run(run, scenarios).values())
    objective, ties = ScenarioOracle(scenarios).exact_best_response((1 / 3,) * 3)
    assert isclose(objective, 0.24514054470174573, abs_tol=1e-12)
    assert ties == ((1, 0, 2, 2),)


def test_global_numerical_audit_is_deterministic() -> None:
    audit = global_update_audit(original_training_pool())
    assert audit["status"] == "PASS"
    assert all(audit["checks"].values())
