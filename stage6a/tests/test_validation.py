import math

import pytest

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.qubo import assignment_from_bits, build_energy_spec, evaluate_qubo


@pytest.fixture
def evaluator() -> ScalingEvaluator:
    return ScalingEvaluator(generate_instance(5))


@pytest.mark.parametrize("value", [0.9, -0.1, math.nan, math.inf, "1"])
def test_scaling_assignment_rejects_nonintegral_or_nonreal_values(
    evaluator: ScalingEvaluator, value
) -> None:
    with pytest.raises(ValueError):
        evaluator.validate_assignment((value, 0, 0, 0, 0))


def test_scaling_assignment_accepts_integral_float(evaluator: ScalingEvaluator) -> None:
    assert evaluator.validate_assignment((1.0, 0, 0, 0, 0)) == (1, 0, 0, 0, 0)


@pytest.mark.parametrize("value", [0.9, -0.1, math.nan, math.inf, "1"])
def test_scaling_bit_decoding_rejects_nonintegral_or_nonreal_values(
    evaluator: ScalingEvaluator, value
) -> None:
    bits = [0] * evaluator.instance.variable_count
    bits[0] = value
    with pytest.raises(ValueError):
        assignment_from_bits(evaluator, bits)


def test_scaling_qubo_rejects_fractional_bits(evaluator: ScalingEvaluator) -> None:
    spec = build_energy_spec(evaluator, (1.0 / 3.0,) * 3, "cost")
    bits = [0] * evaluator.instance.variable_count
    bits[0] = 0.9
    with pytest.raises(ValueError):
        evaluate_qubo(spec.qubo, bits)
