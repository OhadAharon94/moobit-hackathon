import math

import pandas as pd
import pytest

from qera.classiq_solver import parse_routes_cell, process_sample_frame
from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator, validate_assignment


@pytest.mark.parametrize("value", [0.9, -0.1, math.nan, math.inf, "1"])
def test_fractional_or_non_numeric_assignment_values_are_rejected(value) -> None:
    with pytest.raises(ValueError):
        validate_assignment((value, 0, 0, 0))


def test_integral_float_assignment_remains_accepted() -> None:
    assert validate_assignment((1.0, 0, 0, 0)) == (1, 0, 0, 0)


@pytest.mark.parametrize("value", [0.9, -0.1, math.nan, math.inf, "1"])
def test_fractional_or_non_numeric_route_bits_are_rejected(value) -> None:
    with pytest.raises(ValueError):
        parse_routes_cell([value] + [0] * 11)


@pytest.mark.parametrize("count", [1.5, -1, math.nan, math.inf, "2"])
def test_invalid_sample_counts_are_rejected(count) -> None:
    evaluator = Evaluator()
    spec = build_energy_spec(evaluator, INITIAL_SCENARIO_WEIGHTS, "cost")
    frame = pd.DataFrame([{"routes": [0] * 12, "counts": count}])
    with pytest.raises(ValueError):
        process_sample_frame(
            frame,
            evaluator,
            spec,
            INITIAL_SCENARIO_WEIGHTS,
            "cost",
        )
