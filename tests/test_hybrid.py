from dataclasses import dataclass

import pytest

from qera.evaluate import Evaluator
from qera.hybrid import EscalationPolicy, SelectiveHybridSolver
from qera.types import SolveRequest, SolveResult, SolveStatus


@dataclass
class StubSolver:
    result: SolveResult
    calls: int = 0

    def solve(self, request: SolveRequest) -> SolveResult:
        self.calls += 1
        return self.result


REQUEST = SolveRequest("cost", (1.0 / 3.0,) * 3)


def test_good_classical_result_avoids_quantum_execution() -> None:
    classical = StubSolver(SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25))
    quantum = StubSolver(SolveResult(SolveStatus.SUCCESS, (1, 0, 2, 2), 0.24))
    solver = SelectiveHybridSolver(
        Evaluator(), classical, quantum, EscalationPolicy(0.15)
    )

    result = solver.solve(REQUEST)

    assert result.assignment == (0, 1, 1, 2)
    assert result.metadata["decision_source"] == "classical"
    assert result.metadata["quantum_invoked"] is False
    assert classical.calls == 1
    assert quantum.calls == 0


def test_weak_classical_result_invokes_quantum_execution() -> None:
    classical = StubSolver(SolveResult(SolveStatus.SUCCESS, (1, 0, 2, 2), 0.25))
    quantum = StubSolver(SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25))
    solver = SelectiveHybridSolver(
        Evaluator(), classical, quantum, EscalationPolicy(0.20)
    )

    result = solver.solve(REQUEST)

    assert result.assignment == (0, 1, 1, 2)
    assert result.metadata["decision_source"] == "quantum"
    assert result.metadata["quantum_invoked"] is True
    assert classical.calls == 1
    assert quantum.calls == 1


def test_worse_quantum_result_cannot_replace_valid_classical_result() -> None:
    classical_result = SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25)
    classical = StubSolver(classical_result)
    quantum = StubSolver(SolveResult(SolveStatus.SUCCESS, (1, 0, 2, 2), 0.24))
    solver = SelectiveHybridSolver(
        Evaluator(), classical, quantum, EscalationPolicy(0.0)
    )

    result = solver.solve(REQUEST)

    assert result.assignment == classical_result.assignment
    assert result.metadata["decision_source"] == "classical_fallback"
    assert result.metadata["quantum_invoked"] is True
    assert classical_result.metadata == {}


def test_failed_quantum_result_falls_back_to_valid_classical_result() -> None:
    classical = StubSolver(SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25))
    quantum = StubSolver(SolveResult(SolveStatus.EXECUTION_FAILED, None, None))
    solver = SelectiveHybridSolver(
        Evaluator(), classical, quantum, EscalationPolicy(0.0)
    )

    result = solver.solve(REQUEST)

    assert result.assignment == (0, 1, 1, 2)
    assert result.status == SolveStatus.SUCCESS
    assert result.metadata["decision_source"] == "classical_fallback"
    assert result.metadata["quantum_status"] == SolveStatus.EXECUTION_FAILED


def test_infeasible_quantum_result_falls_back_to_valid_classical_result() -> None:
    classical = StubSolver(SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25))
    quantum = StubSolver(SolveResult(SolveStatus.SUCCESS, (0, 0, 0, 0), 0.10))
    solver = SelectiveHybridSolver(
        Evaluator(), classical, quantum, EscalationPolicy(0.0)
    )

    result = solver.solve(REQUEST)

    assert result.assignment == (0, 1, 1, 2)
    assert result.metadata["decision_source"] == "classical_fallback"
    assert result.metadata["quantum_worst_regret"] is None


def test_equal_quality_quantum_result_does_not_displace_classical_result() -> None:
    classical_result = SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25)
    classical = StubSolver(classical_result)
    quantum = StubSolver(SolveResult(SolveStatus.SUCCESS, (0, 1, 1, 2), 0.25))
    solver = SelectiveHybridSolver(
        Evaluator(), classical, quantum, EscalationPolicy(0.0)
    )

    result = solver.solve(REQUEST)

    assert result.assignment == classical_result.assignment
    assert result.metadata["decision_source"] == "classical_fallback"


@pytest.mark.parametrize("threshold", [-0.01, 1.01])
def test_escalation_threshold_is_bounded(threshold: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        EscalationPolicy(threshold)
