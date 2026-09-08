"""Validation and final-test metrics for exact route policies."""

from __future__ import annotations

from statistics import median
from typing import Sequence

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance

from holy_qow_post6a.heldout import build_evaluator

from holy_qow_evolution.scenarios import ExperimentScenario


def evaluate_route(route: tuple[int, ...], scenarios: Sequence[ExperimentScenario]) -> dict:
    rows = []
    for spec in scenarios:
        evaluator = build_evaluator(spec.as_heldout())
        evaluation = evaluator.evaluate(route, "nominal")
        rows.append(
            {
                "scenario_id": spec.scenario_id,
                "category": spec.category,
                "cost": evaluation.cost,
                "regret": evaluator.regret(route, "nominal"),
                "feasible": evaluation.feasible,
                "overflow": evaluation.overflow,
                "maximum_utilization": evaluation.maximum_utilization,
                "weighted_latency": evaluation.latency,
            }
        )
    base = ScalingEvaluator(frozen_instance()).evaluate(route, "nominal")
    return {
        "scenario_count": len(rows),
        "mean_cost": sum(row["cost"] for row in rows) / len(rows),
        "median_cost": median(row["cost"] for row in rows),
        "mean_regret": sum(row["regret"] for row in rows) / len(rows),
        "median_regret": median(row["regret"] for row in rows),
        "worst_regret": max(row["regret"] for row in rows),
        "survival_rate": sum(row["feasible"] for row in rows) / len(rows),
        "violating_scenarios": sum(not row["feasible"] for row in rows),
        "mean_overflow": sum(row["overflow"] for row in rows) / len(rows),
        "maximum_overflow": max(row["overflow"] for row in rows),
        "mean_maximum_utilization": sum(row["maximum_utilization"] for row in rows) / len(rows),
        "worst_maximum_utilization": max(row["maximum_utilization"] for row in rows),
        "mean_weighted_latency": sum(row["weighted_latency"] for row in rows) / len(rows),
        "maximum_weighted_latency": max(row["weighted_latency"] for row in rows),
        "nominal_cost": base.cost,
        "nominal_feasible": base.feasible,
        "rows": rows,
    }
