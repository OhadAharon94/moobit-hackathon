from qera.baselines import (
    load_aware_greedy,
    random_bitstring_frame,
    random_valid_route_frame,
    shortest_path_assignment,
)
from qera.evaluate import Evaluator


def test_shortest_path_control_is_deterministic() -> None:
    assert shortest_path_assignment() == (0, 0, 0, 0)


def test_load_aware_greedy_is_joint_feasible() -> None:
    evaluator = Evaluator()
    assignment = load_aware_greedy(evaluator)
    assert evaluator.is_joint_feasible(assignment)


def test_random_control_budgets_are_exact() -> None:
    bitstrings = random_bitstring_frame(4096, 1701)
    valid_routes = random_valid_route_frame(4096, 1701)
    assert bitstrings["counts"].sum() == 4096
    assert valid_routes["counts"].sum() == 4096
    assert len(bitstrings) <= 4096
    assert len(valid_routes) <= 81

