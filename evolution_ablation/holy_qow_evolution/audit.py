"""Numerical invariant checks for exact adaptation and weight updates."""

from __future__ import annotations

from math import exp, isclose

from holy_qow_evolution.engine import EvolutionRun, ScenarioOracle, run_adaptive_exact, update_weights
from holy_qow_evolution.scenarios import ExperimentScenario


def verify_run(run: EvolutionRun, scenarios: tuple[ExperimentScenario, ...]) -> dict[str, bool]:
    oracle = ScenarioOracle(scenarios)
    checks: dict[str, bool] = {}
    for step in run.steps:
        minimum, ties = oracle.exact_best_response(step.weights)
        prefix = f"t{step.iteration}"
        checks[f"{prefix}_best_response_value"] = isclose(
            step.objective_value, minimum, rel_tol=0.0, abs_tol=1e-12
        )
        checks[f"{prefix}_all_ties"] = step.tied_optima == ties
        checks[f"{prefix}_chosen_first_tie"] = step.assignment == ties[0]
        checks[f"{prefix}_regrets"] = all(
            isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
            for a, b in zip(step.regrets, oracle.regrets(step.assignment), strict=True)
        )
        checks[f"{prefix}_weights_positive"] = all(value > 0.0 for value in step.weights)
        checks[f"{prefix}_weights_normalized"] = isclose(
            sum(step.weights), 1.0, rel_tol=0.0, abs_tol=1e-12
        )
        if step.next_weights is not None and step.pre_mixing_weights is not None:
            clipped, pre, mixed = update_weights(
                step.weights, step.regrets, eta=run.eta, rho=run.rho
            )
            checks[f"{prefix}_clipping"] = clipped == step.clipped_regrets
            checks[f"{prefix}_pre_mixing_formula"] = all(
                isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
                for a, b in zip(pre, step.pre_mixing_weights, strict=True)
            )
            checks[f"{prefix}_mixed_formula"] = all(
                isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
                for a, b in zip(mixed, step.next_weights, strict=True)
            )
    return checks


def global_update_audit(scenarios: tuple[ExperimentScenario, ...]) -> dict:
    weights = (0.1, 0.2, 0.3, 0.4)
    regrets = (-0.2, 0.1, 0.7, 1.8)
    eta = 0.5
    rho = 0.25
    clipped, pre, mixed = update_weights(weights, regrets, eta=eta, rho=rho)
    manual_unnormalized = tuple(
        weight * exp(eta * value) for weight, value in zip(weights, clipped, strict=True)
    )
    manual_total = sum(manual_unnormalized)
    manual_pre = tuple(value / manual_total for value in manual_unnormalized)
    manual_mixed = tuple((1.0 - rho) * value + rho / len(weights) for value in manual_pre)
    _, eta_zero, eta_zero_mixed = update_weights(weights, regrets, eta=0.0, rho=0.0)
    _, rho_pre, rho_mixed = update_weights(weights, regrets, eta=eta, rho=rho)
    uniform = 1.0 / len(weights)
    before_distance = sum(abs(value - uniform) for value in rho_pre)
    after_distance = sum(abs(value - uniform) for value in rho_mixed)
    boost_ratios = tuple(value / weight for value, weight in zip(pre, weights, strict=True))
    monotonic_pairs = tuple(
        boost_ratios[left] <= boost_ratios[right] + 1e-15
        for left in range(len(clipped))
        for right in range(len(clipped))
        if clipped[left] < clipped[right]
    )
    deterministic_a = run_adaptive_exact(scenarios, eta=0.5, iterations=5, rho=0.25)
    deterministic_b = run_adaptive_exact(scenarios, eta=0.5, iterations=5, rho=0.25)
    checks = {
        "clipping_exact": clipped == (0.0, 0.1, 0.7, 1.0),
        "manual_pre_mixing_formula": all(isclose(a, b, rel_tol=0.0, abs_tol=1e-15) for a, b in zip(pre, manual_pre, strict=True)),
        "manual_diversity_formula": all(isclose(a, b, rel_tol=0.0, abs_tol=1e-15) for a, b in zip(mixed, manual_mixed, strict=True)),
        "positive": all(value > 0.0 for value in mixed),
        "normalized": isclose(sum(mixed), 1.0, rel_tol=0.0, abs_tol=1e-15),
        "eta_zero_no_change": all(isclose(a, b, rel_tol=0.0, abs_tol=1e-15) for a, b in zip(weights, eta_zero, strict=True)),
        "eta_zero_rho_zero_no_change": all(isclose(a, b, rel_tol=0.0, abs_tol=1e-15) for a, b in zip(weights, eta_zero_mixed, strict=True)),
        "larger_regret_larger_pre_mixing_boost": all(monotonic_pairs),
        "rho_exact_contraction": isclose(after_distance, (1.0 - rho) * before_distance, rel_tol=0.0, abs_tol=1e-15),
        "deterministic_reproduction": deterministic_a == deterministic_b,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "probe": {
            "weights": weights,
            "regrets": regrets,
            "clipped_regrets": clipped,
            "eta": eta,
            "rho": rho,
            "pre_mixing_weights": pre,
            "mixed_weights": mixed,
            "pre_mixing_l1_from_uniform": before_distance,
            "mixed_l1_from_uniform": after_distance,
        },
    }
