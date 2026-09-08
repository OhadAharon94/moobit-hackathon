import pytest

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.evaluate import Evaluator, all_assignments
from qera.qubo import (
    all_bitstates,
    assignment_from_bits,
    bits_from_assignment,
    build_qubo,
    evaluate_qubo,
    is_one_hot,
)


@pytest.mark.parametrize("mode", ["cost", "regret"])
def test_qubo_matches_direct_objective_on_all_valid_routes(mode: str) -> None:
    evaluator = Evaluator()
    qubo = build_qubo(evaluator, INITIAL_SCENARIO_WEIGHTS, mode)
    errors = [
        abs(
            evaluate_qubo(qubo, bits_from_assignment(assignment))
            - evaluator.weighted_objective(assignment, INITIAL_SCENARIO_WEIGHTS, mode)
        )
        for assignment in all_assignments()
    ]
    assert max(errors) < 1e-12
    assert qubo.one_hot_penalty == 1.0
    assert qubo.verification_summary["invalid_ground_gap"] > 0


def test_assignment_bit_round_trip_and_state_count() -> None:
    assert sum(1 for _ in all_bitstates()) == 4096
    for assignment in all_assignments():
        assert assignment_from_bits(bits_from_assignment(assignment)) == assignment
    assert sum(is_one_hot(bits) for bits in all_bitstates()) == 81


def test_uniform_cost_interaction_count_and_ground() -> None:
    evaluator = Evaluator()
    qubo = build_qubo(evaluator, INITIAL_SCENARIO_WEIGHTS, "cost")
    assert len(qubo.quadratic) == 34
    valid_scored = [
        (evaluate_qubo(qubo, bits_from_assignment(a)), a) for a in all_assignments()
    ]
    minimum = min(value for value, _ in valid_scored)
    assert tuple(a for value, a in valid_scored if value == pytest.approx(minimum)) == (
        (0, 1, 1, 0),
        (1, 0, 0, 1),
    )
