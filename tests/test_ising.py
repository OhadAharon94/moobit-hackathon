import pytest

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.evaluate import Evaluator
from qera.qubo import all_bitstates, build_qubo, evaluate_ising, evaluate_qubo, qubo_to_ising


@pytest.mark.parametrize("mode", ["cost", "regret"])
def test_ising_matches_qubo_on_all_4096_states(mode: str) -> None:
    qubo = build_qubo(Evaluator(), INITIAL_SCENARIO_WEIGHTS, mode)
    ising = qubo_to_ising(qubo)
    maximum_error = max(
        abs(evaluate_qubo(qubo, bits) - evaluate_ising(ising, bits))
        for bits in all_bitstates()
    )
    assert maximum_error < 1e-12

