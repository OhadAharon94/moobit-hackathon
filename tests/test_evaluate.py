import pytest

from qera.evaluate import Evaluator, all_assignments, raw_evaluate
from qera.instance import SCENARIOS


@pytest.fixture(scope="module")
def evaluator() -> Evaluator:
    return Evaluator()


def test_assignment_count_and_normalization(evaluator: Evaluator) -> None:
    assert len(all_assignments()) == 81
    for scenario in SCENARIOS:
        costs = [evaluator.evaluate(a, scenario).cost for a in all_assignments()]
        assert min(costs) >= -1e-12
        assert max(costs) <= 1.0 + 1e-12


def test_known_degradation_capacity_violation(evaluator: Evaluator) -> None:
    evaluation = evaluator.evaluate((0, 1, 1, 0), "degradation")
    assert evaluation.loads[("U", "M1")] == pytest.approx(4.0)
    assert evaluation.utilization[("U", "M1")] == pytest.approx(2.0)
    assert evaluation.overflow == pytest.approx(2.0)
    assert not evaluation.feasible


def test_direct_path_loads_are_consistent() -> None:
    assignment = (1, 0, 2, 2)
    for scenario in SCENARIOS:
        raw = raw_evaluate(assignment, scenario)
        assert sum(raw.loads.values()) > 0
        assert raw.congestion == pytest.approx(
            sum(value * value for value in raw.utilization.values())
        )


def test_feasibility_counts(evaluator: Evaluator) -> None:
    assert {
        scenario.name: sum(
            evaluator.evaluate(assignment, scenario).feasible
            for assignment in all_assignments()
        )
        for scenario in SCENARIOS
    } == {"nominal": 79, "surge": 63, "degradation": 47}
    assert len(evaluator.joint_feasible_assignments()) == 39

