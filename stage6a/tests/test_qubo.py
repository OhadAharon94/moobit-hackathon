from math import isclose

from qera.energy import build_energy_spec as build_frozen_energy_spec
from qera.evaluate import Evaluator
from qera.qubo import build_qubo as build_frozen_qubo

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import core_instances, frozen_instance
from qera_scaling.qubo import build_energy_spec, build_qubo


def test_generic_qubo_reproduces_frozen_d4_coefficients_and_scaling() -> None:
    weights = (1.0 / 3.0,) * 3
    frozen_evaluator = Evaluator()
    generic_evaluator = ScalingEvaluator(frozen_instance())
    frozen = build_frozen_qubo(frozen_evaluator, weights, "cost")
    generic = build_qubo(generic_evaluator, weights, "cost")
    assert isclose(generic.offset, frozen.offset, abs_tol=1e-12)
    assert all(
        isclose(a, b, abs_tol=1e-12)
        for a, b in zip(generic.linear, frozen.linear, strict=True)
    )
    assert generic.quadratic.keys() == frozen.quadratic.keys()
    assert all(
        isclose(generic.quadratic[pair], frozen.quadratic[pair], abs_tol=1e-12)
        for pair in generic.quadratic
    )
    assert generic.one_hot_penalty == frozen.one_hot_penalty == 1.0
    frozen_spec = build_frozen_energy_spec(frozen_evaluator, weights, "cost")
    generic_spec = build_energy_spec(generic_evaluator, weights, "cost")
    assert isclose(generic_spec.phase_offset, frozen_spec.phase_offset, abs_tol=1e-12)
    assert isclose(generic_spec.phase_scale, frozen_spec.phase_scale, abs_tol=1e-12)


def test_all_core_qubos_match_direct_objective_on_every_valid_route() -> None:
    for instance in core_instances():
        evaluator = ScalingEvaluator(instance)
        model = build_qubo(evaluator, (1.0 / 3.0,) * 3, "cost")
        assert model.verification_summary["maximum_one_hot_objective_error"] < 1e-10
        assert model.verification_summary["invalid_ground_gap"] > 1e-8
