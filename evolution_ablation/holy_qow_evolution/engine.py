"""Exact classical best-response loop with audited multiplicative updates."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import exp, isclose, log
from typing import Sequence

from holy_qow_post6a.heldout import build_evaluator

from holy_qow_evolution.scenarios import ExperimentScenario

Assignment = tuple[int, int, int, int]
ENERGY_TOLERANCE = 1e-10


@dataclass(frozen=True)
class EvolutionStep:
    iteration: int
    weights: tuple[float, ...]
    assignment: Assignment
    tied_optima: tuple[Assignment, ...]
    objective_value: float
    regrets: tuple[float, ...]
    clipped_regrets: tuple[float, ...]
    pre_mixing_weights: tuple[float, ...] | None
    next_weights: tuple[float, ...] | None
    entropy: float
    effective_environments: float


@dataclass(frozen=True)
class EvolutionRun:
    scenario_ids: tuple[str, ...]
    eta: float
    iterations: int
    rho: float
    steps: tuple[EvolutionStep, ...]

    @property
    def final_assignment(self) -> Assignment:
        return self.steps[-1].assignment

    @property
    def final_weights(self) -> tuple[float, ...]:
        return self.steps[-1].weights


class ScenarioOracle:
    """Reuse the validated frozen evaluator independently for each environment."""

    def __init__(self, scenarios: Sequence[ExperimentScenario]) -> None:
        if not scenarios:
            raise ValueError("at least one scenario is required")
        self.scenarios = tuple(scenarios)
        self.evaluators = tuple(build_evaluator(item.as_heldout()) for item in scenarios)
        self.assignments: tuple[Assignment, ...] = tuple(product(range(3), repeat=4))  # type: ignore[assignment]

    def evaluations(self, route: Assignment):
        return tuple(evaluator.evaluate(route, "nominal") for evaluator in self.evaluators)

    def regrets(self, route: Assignment) -> tuple[float, ...]:
        return tuple(evaluator.regret(route, "nominal") for evaluator in self.evaluators)

    def joint_feasible_assignments(self) -> tuple[Assignment, ...]:
        return tuple(route for route in self.assignments if all(item.feasible for item in self.evaluations(route)))

    def exact_best_response(
        self, weights: Sequence[float]
    ) -> tuple[float, tuple[Assignment, ...]]:
        if len(weights) != len(self.scenarios):
            raise ValueError("one weight is required per scenario")
        domain = self.joint_feasible_assignments()
        if not domain:
            raise ValueError("declared training environments have no jointly feasible route")
        scored = tuple(
            (
                sum(
                    float(weight) * evaluation.cost
                    for weight, evaluation in zip(weights, self.evaluations(route), strict=True)
                ),
                route,
            )
            for route in domain
        )
        minimum = min(value for value, _ in scored)
        ties = tuple(sorted(route for value, route in scored if isclose(value, minimum, abs_tol=ENERGY_TOLERANCE)))
        return minimum, ties


def entropy(weights: Sequence[float]) -> float:
    if any(value <= 0.0 for value in weights):
        raise ValueError("entropy requires strictly positive weights")
    return -sum(float(value) * log(float(value)) for value in weights)


def update_weights(
    weights: Sequence[float],
    regrets: Sequence[float],
    *,
    eta: float,
    rho: float,
    r_max: float = 1.0,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if len(weights) != len(regrets) or not weights:
        raise ValueError("weight and regret vectors must have equal nonzero length")
    if eta < 0.0:
        raise ValueError("eta must be nonnegative")
    if not 0.0 <= rho <= 1.0:
        raise ValueError("rho must be in [0, 1]")
    if r_max <= 0.0:
        raise ValueError("r_max must be positive")
    current = tuple(float(value) for value in weights)
    if any(not value > 0.0 for value in current) or not isclose(sum(current), 1.0, abs_tol=1e-12):
        raise ValueError("current weights must be positive and normalized")
    clipped = tuple(min(r_max, max(0.0, float(value))) for value in regrets)
    unnormalized = tuple(weight * exp(eta * regret) for weight, regret in zip(current, clipped, strict=True))
    total = sum(unnormalized)
    pre_mixing = tuple(value / total for value in unnormalized)
    uniform = 1.0 / len(current)
    mixed = tuple((1.0 - rho) * value + rho * uniform for value in pre_mixing)
    if any(not value > 0.0 for value in mixed):
        raise AssertionError("weight update produced a nonpositive weight")
    if not isclose(sum(mixed), 1.0, abs_tol=1e-12):
        raise AssertionError("weight update is not normalized")
    return clipped, pre_mixing, mixed


def run_adaptive_exact(
    scenarios: Sequence[ExperimentScenario],
    *,
    eta: float,
    iterations: int,
    rho: float,
) -> EvolutionRun:
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    oracle = ScenarioOracle(scenarios)
    weights = (1.0 / len(scenarios),) * len(scenarios)
    steps: list[EvolutionStep] = []
    for iteration in range(iterations):
        objective, ties = oracle.exact_best_response(weights)
        route = ties[0]
        regrets = oracle.regrets(route)
        current_entropy = entropy(weights)
        clipped: tuple[float, ...]
        pre_mixing: tuple[float, ...] | None
        next_weights: tuple[float, ...] | None
        if iteration + 1 < iterations:
            clipped, pre_mixing, next_weights = update_weights(
                weights, regrets, eta=eta, rho=rho
            )
        else:
            clipped = tuple(min(1.0, max(0.0, value)) for value in regrets)
            pre_mixing = None
            next_weights = None
        steps.append(
            EvolutionStep(
                iteration=iteration,
                weights=tuple(weights),
                assignment=route,
                tied_optima=ties,
                objective_value=objective,
                regrets=regrets,
                clipped_regrets=clipped,
                pre_mixing_weights=pre_mixing,
                next_weights=next_weights,
                entropy=current_entropy,
                effective_environments=exp(current_entropy),
            )
        )
        if next_weights is not None:
            weights = next_weights
    return EvolutionRun(
        scenario_ids=tuple(item.scenario_id for item in scenarios),
        eta=float(eta),
        iterations=iterations,
        rho=float(rho),
        steps=tuple(steps),
    )
