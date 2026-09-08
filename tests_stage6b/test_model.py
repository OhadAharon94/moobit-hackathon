from classiq import create_model
import pytest

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance
from qera_scaling.qubo import build_energy_spec
from qera_stage6b.model import (
    build_constrained_qaoa_main,
    build_initial_state_main,
    build_single_demand_mixer_main,
)


WEIGHTS = (1.0 / 3.0,) * 3


def test_initial_state_model_uses_dicke_one_excitation_preparation() -> None:
    qmod = create_model(build_initial_state_main(4))
    assert "prepare_dicke_state" in qmod
    assert "hadamard_transform" not in qmod


def test_constrained_model_contains_xy_pairs_and_frozen_cost() -> None:
    evaluator = ScalingEvaluator(frozen_instance())
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    qmod = create_model(build_constrained_qaoa_main(spec, 4, depth=1))
    assert "RXX" in qmod
    assert "RYY" in qmod
    assert "prepare_dicke_state" in qmod
    assert "cost_layer" in qmod
    assert "hadamard_transform" not in qmod


@pytest.mark.parametrize("initial_route", [0, 1, 2])
def test_single_demand_model_accepts_each_valid_basis_state(initial_route: int) -> None:
    qmod = create_model(build_single_demand_mixer_main(initial_route))
    assert "RXX" in qmod
    assert "RYY" in qmod


def test_model_rejects_invalid_dimensions_and_depth() -> None:
    evaluator = ScalingEvaluator(frozen_instance())
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    with pytest.raises(ValueError):
        build_initial_state_main(0)
    with pytest.raises(ValueError):
        build_single_demand_mixer_main(3)
    with pytest.raises(ValueError):
        build_constrained_qaoa_main(spec, 4, depth=0)
    with pytest.raises(ValueError):
        build_constrained_qaoa_main(spec, 3, depth=1)
