import pytest

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.exact import exact_adaptive_run
from qera.qubo import all_bitstates, assignment_from_bits


@pytest.mark.parametrize("mode", ["cost", "regret"])
def test_affine_scaling_preserves_energy_order_and_ties(mode: str) -> None:
    spec = build_energy_spec(Evaluator(), INITIAL_SCENARIO_WEIGHTS, mode, "base")
    unscaled = sorted((spec.unscaled_energy(bits), tuple(bits)) for bits in all_bitstates())
    scaled = sorted((spec.transformed_energy(bits), tuple(bits)) for bits in all_bitstates())
    assert [bits for _, bits in unscaled] == [bits for _, bits in scaled]


@pytest.mark.parametrize("mode", ["cost", "regret"])
def test_all_six_adaptive_aligned_energies_have_feasible_ground_states(mode: str) -> None:
    evaluator = Evaluator()
    for record in exact_adaptive_run(evaluator, mode):
        spec = build_energy_spec(
            evaluator, record.weights, mode, energy_mode="aligned"
        )
        assert spec.qubo.one_hot_penalty == 1.0
        assert spec.capacity_penalty == 1.0
        assert spec.verification_summary["capacity_gap"] > 0
        assert spec.verification_summary["all_ground_states_joint_feasible"]
        assert all(
            assignment_from_bits(bits) is not None
            for bits in all_bitstates()
            if abs(spec.unscaled_energy(bits) - spec.verification_summary["ground_energy"])
            < 1e-8
        )


def test_unrestricted_base_ground_is_degradation_infeasible() -> None:
    evaluator = Evaluator()
    spec = build_energy_spec(evaluator, INITIAL_SCENARIO_WEIGHTS, "cost", "base")
    minimum = min(spec.unscaled_energy(bits) for bits in all_bitstates())
    assignments = tuple(
        assignment_from_bits(bits)
        for bits in all_bitstates()
        if abs(spec.unscaled_energy(bits) - minimum) < 1e-8
    )
    assert tuple(sorted(assignments)) == ((0, 1, 1, 0), (1, 0, 0, 1))
    assert all(
        not evaluator.evaluate(assignment, "degradation").feasible
        for assignment in assignments
    )
