import pytest

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.evaluate import Evaluator
from qera.exact import (
    exact_adaptive_run,
    minimax_regret_optima,
    scenario_optima,
    weighted_optima,
)


@pytest.fixture(scope="module")
def evaluator() -> Evaluator:
    return Evaluator()


def test_scenario_optimum_sets(evaluator: Evaluator) -> None:
    assert scenario_optima(evaluator, "nominal")[1] == (
        (0, 1, 1, 0),
        (1, 0, 0, 1),
    )
    assert scenario_optima(evaluator, "surge")[1] == ((1, 0, 2, 2),)
    assert scenario_optima(evaluator, "degradation")[1] == (
        (0, 1, 1, 1),
        (1, 0, 1, 1),
        (1, 1, 0, 1),
        (1, 1, 1, 0),
    )


def test_regret_reference_plans(evaluator: Evaluator) -> None:
    cost_plan = (1, 0, 2, 2)
    minimax_plan = (0, 1, 1, 2)
    assert [evaluator.regret(cost_plan, name) for name in ("nominal", "surge", "degradation")] == pytest.approx(
        [0.038886, 0.0, 0.338081], abs=1e-6
    )
    assert [evaluator.regret(minimax_plan, name) for name in ("nominal", "surge", "degradation")] == pytest.approx(
        [0.123229, 0.108938, 0.112441], abs=1e-6
    )


def test_uniform_cost_and_regret_controls(evaluator: Evaluator) -> None:
    assert weighted_optima(
        evaluator, INITIAL_SCENARIO_WEIGHTS, "cost", joint_feasible=True
    )[1] == ((1, 0, 2, 2),)
    uniform_regret = weighted_optima(
        evaluator, INITIAL_SCENARIO_WEIGHTS, "regret", joint_feasible=True
    )[1]
    expected_tie = ((0, 1, 1, 2), (1, 0, 1, 2))
    assert uniform_regret == expected_tie
    assert minimax_regret_optima(evaluator)[1] == expected_tie


def test_cost_adaptive_trajectory(evaluator: Evaluator) -> None:
    records = exact_adaptive_run(evaluator, "cost")
    assert [record.assignment for record in records] == [
        (1, 0, 2, 2),
        (1, 0, 2, 2),
        (0, 1, 1, 2),
    ]
    expected_weights = [
        (0.333333, 0.333333, 0.333333),
        (0.302057, 0.290537, 0.407406),
        (0.267068, 0.247085, 0.485847),
    ]
    for record, expected in zip(records, expected_weights, strict=True):
        assert record.weights == pytest.approx(expected, abs=1e-6)


def test_regret_adaptive_stays_on_static_minimax(evaluator: Evaluator) -> None:
    records = exact_adaptive_run(evaluator, "regret")
    assert records[0].assignment == (0, 1, 1, 2)
