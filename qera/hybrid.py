"""Selective classical-to-quantum escalation for Holy Qow."""

from __future__ import annotations

from dataclasses import dataclass

from qera.adaptive import InnerSolver
from qera.evaluate import Evaluator
from qera.instance import SCENARIOS
from qera.types import SolveRequest, SolveResult, SolveStatus


@dataclass(frozen=True)
class EscalationPolicy:
    """Quality threshold controlling whether quantum computation is invoked."""

    maximum_classical_worst_regret: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.maximum_classical_worst_regret <= 1.0:
            raise ValueError("maximum classical worst regret must be between 0 and 1")


class SelectiveHybridSolver:
    """Use the classical result unless policy requires a quantum escalation."""

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

    def _worst_regret(self, result: SolveResult) -> float | None:
        if result.status != SolveStatus.SUCCESS or result.assignment is None:
            return None
        if not self.evaluator.is_joint_feasible(result.assignment):
            return None
        return max(
            self.evaluator.regret(result.assignment, scenario)
            for scenario in SCENARIOS
        )

    def solve(self, request: SolveRequest) -> SolveResult:
        classical = self.classical_solver.solve(request)
        classical_regret = self._worst_regret(classical)
        if (
            classical_regret is not None
            and classical_regret <= self.policy.maximum_classical_worst_regret
        ):
            classical.metadata.update(
                {
                    "decision_source": "classical",
                    "quantum_invoked": False,
                    "classical_worst_regret": classical_regret,
                    "escalation_threshold": self.policy.maximum_classical_worst_regret,
                }
            )
            return classical

        quantum = self.quantum_solver.solve(request)
        quantum.metadata.update(
            {
                "decision_source": "quantum",
                "quantum_invoked": True,
                "classical_status": classical.status,
                "classical_worst_regret": classical_regret,
                "escalation_threshold": self.policy.maximum_classical_worst_regret,
            }
        )
        return quantum
