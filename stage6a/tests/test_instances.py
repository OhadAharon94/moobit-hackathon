from qera_scaling.acceptance import require_accepted
from qera_scaling.instances import CORE_SIZES, core_instances


def test_core_grid_is_deterministic_and_accepted() -> None:
    first = core_instances()
    second = core_instances()
    assert tuple(instance.demand_count for instance in first) == CORE_SIZES
    assert [instance.to_dict() for instance in first] == [
        instance.to_dict() for instance in second
    ]
    for instance in first:
        report = require_accepted(instance)
        assert report["valid_assignment_count"] == 3 ** instance.demand_count
        assert report["joint_feasible_count"] > 0
