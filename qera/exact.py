"""Exact enumeration, optimum sets, and adaptive control trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Iterable, Sequence

from qera.config import (
    ADAPTIVE_ETA,
    ADAPTIVE_SOLVES,
    ENERGY_TOLERANCE,
    INITIAL_SCENARIO_WEIGHTS,
)
from qera.evaluate import Evaluator, all_assignments
from qera.instance import SCENARIOS
from qera.types import Assignment


@dataclass(frozen=True)
class AdaptiveRecord:
    iteration: int
    weights: tuple[float, ...]
    assignment: Assignment
    objective_value: float
    regrets: tuple[float, ...]
    worst_regret: float


def argmin_assignments(
    scored: Iterable[tuple[Assignment, float]], tolerance: float = ENERGY_TOLERANCE
) -> tuple[float, tuple[Assignment, ...]]:
    materialized = tuple(scored)
    if not materialized:
        raise ValueError("cannot minimize an empty assignment set")
    minimum = min(value for _, value in materialized)
    optima = tuple(
        sorted(
            assignment
            for assignment, value in materialized
            if abs(value - minimum) <= tolerance
        )
    )
    return minimum, optima


def scenario_optima(
    evaluator: Evaluator, scenario_name: str
) -> tuple[float, tuple[Assignment, ...]]:
    scored = []
    for assignment in all_assignments():
        evaluation = evaluator.evaluate(assignment, scenario_name)
        if evaluation.feasible:
            scored.append((assignment, evaluation.cost))
    return argmin_assignments(scored)


def weighted_optima(
    evaluator: Evaluator,
    weights: Sequence[float],
    mode: str,
    *,
    joint_feasible: bool,
) -> tuple[float, tuple[Assignment, ...]]:
    domain = (
        evaluator.joint_feasible_assignments() if joint_feasible else all_assignments()
    )
    return argmin_assignments(
        (assignment, evaluator.weighted_objective(assignment, weights, mode))
        for assignment in domain
    )


def minimax_regret_optima(
    evaluator: Evaluator,
) -> tuple[float, tuple[Assignment, ...]]:
    return argmin_assignments(
        (
            assignment,
            max(evaluator.regret(assignment, scenario) for scenario in SCENARIOS),
        )
        for assignment in evaluator.joint_feasible_assignments()
    )


def update_weights(
    weights: Sequence[float], regrets: Sequence[float], eta: float = ADAPTIVE_ETA
) -> tuple[float, ...]:
    if len(weights) != len(regrets):
        raise ValueError("weight and regret vectors must have the same length")
    unnormalized = [
        float(weight) * exp(eta * min(1.0, max(0.0, float(regret))))
        for weight, regret in zip(weights, regrets, strict=True)
    ]
    total = sum(unnormalized)
    return tuple(value / total for value in unnormalized)


def exact_adaptive_run(
    evaluator: Evaluator,
    mode: str,
    solves: int = ADAPTIVE_SOLVES,
) -> tuple[AdaptiveRecord, ...]:
    weights = INITIAL_SCENARIO_WEIGHTS
    records: list[AdaptiveRecord] = []
    for iteration in range(solves):
        objective, optima = weighted_optima(
            evaluator, weights, mode, joint_feasible=True
        )
        assignment = optima[0]
        regrets = tuple(evaluator.regret(assignment, scenario) for scenario in SCENARIOS)
        records.append(
            AdaptiveRecord(
                iteration=iteration,
                weights=tuple(weights),
                assignment=assignment,
                objective_value=objective,
                regrets=regrets,
                worst_regret=max(regrets),
            )
        )
        if iteration + 1 < solves:
            weights = update_weights(weights, regrets)
    return tuple(records)
