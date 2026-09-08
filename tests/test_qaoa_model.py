from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.qaoa_model import create_qmod, make_classical_cost, make_qmod_cost
from qera.qubo import all_bitstates


def test_qmod_and_classical_cost_builders_share_one_energy() -> None:
    spec = build_energy_spec(
        Evaluator(), INITIAL_SCENARIO_WEIGHTS, "cost", energy_mode="base"
    )
    classical_cost = make_classical_cost(spec)
    qmod_cost = make_qmod_cost(spec)
    assert max(
        abs(classical_cost(bits) - qmod_cost(bits)) for bits in all_bitstates()
    ) < 1e-12


def test_base_qaoa_model_serializes_without_platform_access() -> None:
    spec = build_energy_spec(
        Evaluator(), INITIAL_SCENARIO_WEIGHTS, "cost", energy_mode="base"
    )
    qmod = create_qmod(spec, depth=1)
    assert isinstance(qmod, str)
    assert '"name":"main"' in qmod.replace(" ", "")
    assert "routes" in qmod
    assert "params" in qmod

