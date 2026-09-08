import pandas as pd
import pytest

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.postprocess import parse_routes_cell, process_sample_frame
from qera_scaling.qubo import bits_from_assignment, build_energy_spec


def test_scaling_sample_decoder_aggregates_named_output_and_scores() -> None:
    evaluator = ScalingEvaluator(generate_instance(5))
    weights = (1.0 / 3.0,) * 3
    spec = build_energy_spec(evaluator, weights, "cost")
    bits = bits_from_assignment(evaluator, (0, 1, 2, 0, 1))
    frame = pd.DataFrame(
        [
            {"routes": str(list(bits)), "counts": 3, "bitstring": "provider-a"},
            {"routes": list(bits), "counts": 2, "bitstring": "provider-b"},
        ]
    )
    processed, summary = process_sample_frame(
        frame, evaluator, spec, weights, declared_shots=5
    )
    assert len(processed) == 1
    assert processed.iloc[0]["assignment"] == "[0, 1, 2, 0, 1]"
    assert processed.iloc[0]["counts"] == 5
    assert summary["one_hot_probability"] == 1.0


@pytest.mark.parametrize("value", [[0] * 14, [0] * 14 + [0.9], "not-a-list"])
def test_scaling_route_parser_rejects_invalid_values(value) -> None:
    with pytest.raises((ValueError, SyntaxError)):
        parse_routes_cell(value, 15)


@pytest.mark.parametrize("count", [1.5, -1, "2"])
def test_scaling_sample_decoder_rejects_invalid_counts(count) -> None:
    evaluator = ScalingEvaluator(generate_instance(5))
    spec = build_energy_spec(evaluator, (1.0 / 3.0,) * 3, "cost")
    frame = pd.DataFrame([{"routes": [0] * 15, "counts": count}])
    with pytest.raises(ValueError):
        process_sample_frame(frame, evaluator, spec, (1.0 / 3.0,) * 3)
