import json

from qera_scaling.classiq_model import create_qmod, make_classical_cost, make_qmod_cost
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.qubo import build_energy_spec


def test_variable_width_models_serialize_locally() -> None:
    for demand_count in (4, 5, 6, 8):
        evaluator = ScalingEvaluator(generate_instance(demand_count))
        spec = build_energy_spec(evaluator, (1.0 / 3.0,) * 3, "cost")
        model = json.loads(create_qmod(spec, depth=1))
        assert "functions" in model
        main = next(function for function in model["functions"] if function["name"] == "main")
        routes = next(
            declaration
            for declaration in main["positional_arg_declarations"]
            if declaration["name"] == "routes"
        )
        assert routes["direction"] == "output"
        assert routes["quantum_type"]["kind"] == "qvec"
        assert routes["quantum_type"]["length"]["expr"] == str(3 * demand_count)


def test_classical_and_qmod_cost_builders_match_on_binary_inputs() -> None:
    evaluator = ScalingEvaluator(generate_instance(5))
    spec = build_energy_spec(evaluator, (1.0 / 3.0,) * 3, "cost")
    classical = make_classical_cost(spec)
    qmod = make_qmod_cost(spec)
    for route in list(evaluator.all_assignments())[:20]:
        bits = [0] * evaluator.instance.variable_count
        for demand_index, path_index in enumerate(route):
            bits[evaluator.instance.variable_index(demand_index, path_index)] = 1
        assert abs(classical(bits) - qmod(bits)) < 1e-12
