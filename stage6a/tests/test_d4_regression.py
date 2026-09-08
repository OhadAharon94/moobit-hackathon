from math import isclose

from qera.evaluate import Evaluator
from qera.instance import SCENARIOS

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance


def test_generic_evaluator_reproduces_every_d4_value() -> None:
    frozen = Evaluator()
    generic = ScalingEvaluator(frozen_instance())
    for assignment in generic.all_assignments():
        assert generic.is_joint_feasible(assignment) == frozen.is_joint_feasible(assignment)
        for scenario in SCENARIOS:
            expected = frozen.evaluate(assignment, scenario)
            actual = generic.evaluate(assignment, scenario.name)
            for field in (
                "latency",
                "congestion",
                "normalized_latency",
                "normalized_congestion",
                "cost",
                "maximum_utilization",
                "overflow",
            ):
                assert isclose(getattr(actual, field), getattr(expected, field), abs_tol=1e-12)
            assert actual.feasible == expected.feasible
            assert isclose(
                generic.regret(assignment, scenario.name),
                frozen.regret(assignment, scenario),
                abs_tol=1e-12,
            )


def test_d4_combinatorial_dimensions_are_preserved() -> None:
    instance = frozen_instance()
    assert instance.demand_count == 4
    assert instance.paths_per_demand == 3
    assert instance.scenario_count == 3
    assert instance.variable_count == 12
    assert len(tuple(ScalingEvaluator(instance).all_assignments())) == 81
