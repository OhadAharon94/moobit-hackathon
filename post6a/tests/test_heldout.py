from __future__ import annotations

from collections import Counter

from holy_qow_post6a.heldout import (
    build_evaluator,
    heldout_scenarios,
    route_manifest,
)


def test_heldout_manifest_is_balanced_unique_and_has_no_edge_removal() -> None:
    scenarios = heldout_scenarios()
    assert len(scenarios) == 24
    assert len({scenario.scenario_id for scenario in scenarios}) == 24
    assert Counter(scenario.category for scenario in scenarios) == {
        "demand": 6,
        "capacity": 6,
        "latency": 6,
        "combined": 6,
    }
    assert all(
        multiplier > 0
        for scenario in scenarios
        for multiplier in scenario.capacity_multipliers.values()
    )


def test_every_heldout_scenario_has_a_feasible_fixed_route() -> None:
    for scenario in heldout_scenarios():
        evaluator = build_evaluator(scenario)
        assert evaluator.joint_feasible_assignments(), scenario.scenario_id


def test_route_identities_are_fixed_before_heldout_evaluation() -> None:
    manifest = route_manifest()
    assert manifest["selection_policy"] == (
        "all route identities fixed from pre-held-out artifacts"
    )
    assert [route["route_id"] for route in manifest["routes"]] == [
        "nominal_only",
        "static_uniform_multiscenario",
        "exact_adaptive",
        "qaoa_adaptive",
        "exact_pure_minimax",
    ]
    assert all(source["sha256"] for source in manifest["source_artifacts"])
