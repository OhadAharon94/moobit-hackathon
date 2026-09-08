import pandas as pd
import pytest

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.classiq_solver import parse_routes_cell, process_sample_frame


def test_known_basis_state_decodes_in_canonical_order() -> None:
    bits = [0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0]
    assert parse_routes_cell(str(bits)) == tuple(bits)
    evaluator = Evaluator()
    spec = build_energy_spec(
        evaluator, INITIAL_SCENARIO_WEIGHTS, "cost", energy_mode="base"
    )
    frame = pd.DataFrame(
        [
            {"routes": str(bits), "counts": 3, "bitstring": "known"},
            {"routes": bits, "counts": 2, "bitstring": "known"},
        ]
    )
    processed, summary = process_sample_frame(
        frame,
        evaluator,
        spec,
        INITIAL_SCENARIO_WEIGHTS,
        "cost",
        declared_shots=5,
    )
    assert len(processed) == 1
    assert processed.iloc[0]["assignment"] == "[1, 0, 2, 1]"
    assert processed.iloc[0]["counts"] == 5
    assert summary["total_shots"] == 5


@pytest.mark.parametrize(
    "value",
    ["not-a-list", [0] * 11, [0] * 11 + [2]],
)
def test_invalid_named_route_output_is_rejected(value) -> None:
    with pytest.raises((ValueError, SyntaxError)):
        parse_routes_cell(value)

