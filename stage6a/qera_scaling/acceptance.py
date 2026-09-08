"""Acceptance checks for deterministic scaling instances."""

from __future__ import annotations

from collections import Counter
from math import isclose

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.model import ScalingInstance


def acceptance_report(instance: ScalingInstance) -> dict:
    instance.validate_structure()
    evaluator = ScalingEvaluator(instance)
    assignments = tuple(evaluator.all_assignments())
    feasible_counts = {}
    scenario_optima = {}
    congestion_ranges = {}
    for scenario in instance.scenarios:
        feasible_routes = [
            route for route in assignments if evaluator.evaluate(route, scenario).feasible
        ]
        feasible_counts[scenario.name] = len(feasible_routes)
        best = min(evaluator.evaluate(route, scenario).cost for route in feasible_routes)
        scenario_optima[scenario.name] = [
            list(route)
            for route in feasible_routes
            if isclose(evaluator.evaluate(route, scenario).cost, best, abs_tol=1e-10)
        ]
        congestion_values = [
            evaluator.raw_evaluate(route, scenario).congestion for route in assignments
        ]
        congestion_ranges[scenario.name] = {
            "minimum": min(congestion_values),
            "maximum": max(congestion_values),
        }
    optimum_sets = [
        {tuple(route) for route in routes} for routes in scenario_optima.values()
    ]
    shared_usage = Counter(
        edge
        for demand_paths in instance.path_edges
        for edges in demand_paths
        for edge in set(edges)
    )
    joint_count = sum(evaluator.is_joint_feasible(route) for route in assignments)
    checks = {
        "three_paths_per_demand": all(len(d.paths) == 3 for d in instance.demands),
        "all_scenarios_have_feasible_routes": all(
            count > 0 for count in feasible_counts.values()
        ),
        "joint_feasible_routes_exist": joint_count > 0,
        "shared_resources_exist": any(count > 3 for count in shared_usage.values()),
        "congestion_is_nonconstant": all(
            values["maximum"] - values["minimum"] > 1e-10
            for values in congestion_ranges.values()
        ),
        "scenarios_create_conflicting_pressure": not set.intersection(*optimum_sets),
        "surge_changes_volumes": instance.scenarios[1].volumes
        != instance.scenarios[0].volumes,
        "degradation_changes_capacity": bool(instance.scenarios[2].capacity_overrides),
    }
    return {
        "instance_id": instance.instance_id,
        "D": instance.demand_count,
        "valid_assignment_count": len(assignments),
        "feasible_by_scenario": feasible_counts,
        "joint_feasible_count": joint_count,
        "joint_feasible_fraction": joint_count / len(assignments),
        "scenario_optima": scenario_optima,
        "congestion_ranges": congestion_ranges,
        "maximum_candidate_edge_demand_usage": max(shared_usage.values()),
        "checks": checks,
        "accepted": all(checks.values()),
    }


def require_accepted(instance: ScalingInstance) -> dict:
    report = acceptance_report(instance)
    failed = [name for name, passed in report["checks"].items() if not passed]
    if failed:
        raise ValueError(f"instance {instance.instance_id} rejected: {failed}")
    return report
