"""Solver-agnostic multiplicative-weights outer loop."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qera.config import ADAPTIVE_SOLVES, INITIAL_SCENARIO_WEIGHTS
from qera.evaluate import Evaluator
from qera.exact import update_weights
from qera.instance import SCENARIOS
from qera.types import Assignment, SolveRequest, SolveResult, SolveStatus


class InnerSolver(Protocol):
    def solve(self, request: SolveRequest) -> SolveResult: ...


@dataclass(frozen=True)
class AdaptiveStep:
    iteration: int
    request: SolveRequest
    result: SolveResult
    regrets: tuple[float, ...]
    worst_regret: float
    best_so_far: Assignment


@dataclass(frozen=True)
class AdaptiveRun:
    status: SolveStatus
    steps: tuple[AdaptiveStep, ...]
    best_assignment: Assignment | None


def run_adaptive(
    solver: InnerSolver,
    evaluator: Evaluator,
    objective_mode: str,
    *,
    solves: int = ADAPTIVE_SOLVES,
    seed: int = 1701,
) -> AdaptiveRun:
    """Run the same outer loop for exact or measured quantum inner solvers."""

    weights = INITIAL_SCENARIO_WEIGHTS
    steps: list[AdaptiveStep] = []
    best_assignment: Assignment | None = None
    best_key: tuple[float, Assignment] | None = None
    for iteration in range(solves):
        request = SolveRequest(
            objective_mode=objective_mode,
            scenario_weights=tuple(weights),
            energy_mode="base",
            seed=seed + iteration,
        )
        result = solver.solve(request)
        if result.status != SolveStatus.SUCCESS or result.assignment is None:
            return AdaptiveRun(result.status, tuple(steps), best_assignment)
        if not evaluator.is_joint_feasible(result.assignment):
            raise ValueError("inner solver returned an assignment outside the accepted set")
        regrets = tuple(
            evaluator.regret(result.assignment, scenario) for scenario in SCENARIOS
        )
        key = (max(regrets), result.assignment)
        if best_key is None or key < best_key:
            best_key = key
            best_assignment = result.assignment
        steps.append(
            AdaptiveStep(
                iteration=iteration,
                request=request,
                result=result,
                regrets=regrets,
                worst_regret=max(regrets),
                best_so_far=best_assignment,
            )
        )
        if iteration + 1 < solves:
            weights = update_weights(weights, regrets)
    return AdaptiveRun(SolveStatus.SUCCESS, tuple(steps), best_assignment)
