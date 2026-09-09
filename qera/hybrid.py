"""Selective classical-to-quantum escalation for Holy Qow."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isclose

from qera.adaptive import InnerSolver
from qera.evaluate import Evaluator
from qera.instance import SCENARIOS
from qera.types import SolveRequest, SolveResult, SolveStatus

SCORE_TOLERANCE = 1e-12


@dataclass(frozen=True)
class EscalationPolicy:
    """Quality threshold controlling whether quantum computation is invoked."""

    maximum_classical_worst_regret: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.maximum_classical_worst_regret <= 1.0:
            raise ValueError("maximum classical worst regret must be between 0 and 1")


class SelectiveHybridSolver:
    """Experimentally escalate weak classical results without weakening safety."""

    def __init__(
        self,
        evaluator: Evaluator,
        classical_solver: InnerSolver,
        quantum_solver: InnerSolver,
        policy: EscalationPolicy,
    ) -> None:
        self.evaluator = evaluator
        self.classical_solver = classical_solver
        self.quantum_solver = quantum_solver
        self.policy = policy

    def _score(
        self, result: SolveResult, request: SolveRequest
    ) -> tuple[float, float] | None:
        if result.status != SolveStatus.SUCCESS or result.assignment is None:
            return None
        if not self.evaluator.is_joint_feasible(result.assignment):
            return None
        worst_regret = max(
            self.evaluator.regret(result.assignment, scenario)
            for scenario in SCENARIOS
        )
        objective = self.evaluator.weighted_objective(
            result.assignment, request.scenario_weights, request.objective_mode
        )
        return worst_regret, objective

    @staticmethod
    def _annotate(result: SolveResult, **metadata: object) -> SolveResult:
        """Return an annotated copy and leave solver-owned results untouched."""

        return replace(result, metadata={**result.metadata, **metadata})

    @staticmethod
    def _strictly_better(
        candidate: tuple[float, float], baseline: tuple[float, float]
    ) -> bool:
        if candidate[0] < baseline[0] - SCORE_TOLERANCE:
            return True
        return isclose(
            candidate[0], baseline[0], rel_tol=0.0, abs_tol=SCORE_TOLERANCE
        ) and candidate[1] < baseline[1] - SCORE_TOLERANCE

    def solve(self, request: SolveRequest) -> SolveResult:
        classical = self.classical_solver.solve(request)
        classical_score = self._score(classical, request)
        classical_regret = classical_score[0] if classical_score is not None else None
        if (
            classical_regret is not None
            and classical_regret <= self.policy.maximum_classical_worst_regret
        ):
            return self._annotate(
                classical,
                decision_source="classical",
                quantum_invoked=False,
                classical_worst_regret=classical_regret,
                escalation_threshold=self.policy.maximum_classical_worst_regret,
            )

        quantum = self.quantum_solver.solve(request)
        quantum_score = self._score(quantum, request)
        quantum_regret = quantum_score[0] if quantum_score is not None else None
        common_metadata = {
            "quantum_invoked": True,
            "classical_status": classical.status,
            "classical_worst_regret": classical_regret,
            "quantum_status": quantum.status,
            "quantum_worst_regret": quantum_regret,
            "escalation_threshold": self.policy.maximum_classical_worst_regret,
        }

        if quantum_score is not None and (
            classical_score is None
            or self._strictly_better(quantum_score, classical_score)
        ):
            return self._annotate(
                quantum, decision_source="quantum", **common_metadata
            )

        if classical_score is not None:
            return self._annotate(
                classical,
                decision_source="classical_fallback",
                **common_metadata,
            )

        return self._annotate(
            quantum,
            decision_source="quantum_failure",
            **common_metadata,
        )
