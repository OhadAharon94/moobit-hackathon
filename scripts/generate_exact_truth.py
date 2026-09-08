"""Generate the reproducible Stage 1 exact-truth artifact."""

from __future__ import annotations

from pathlib import Path

from qera.config import INITIAL_SCENARIO_WEIGHTS, PLAN_VERSION, SCHEMA_VERSION
from qera.evaluate import Evaluator, all_assignments
from qera.exact import (
    exact_adaptive_run,
    minimax_regret_optima,
    scenario_optima,
    weighted_optima,
)
from qera.instance import SCENARIOS
from qera.records import write_json


def main() -> None:
    evaluator = Evaluator()
    scenario_results = {}
    for scenario in SCENARIOS:
        optimum, assignments = scenario_optima(evaluator, scenario.name)
        scenario_results[scenario.name] = {
            "feasible_count": sum(
                evaluator.evaluate(assignment, scenario).feasible
                for assignment in all_assignments()
            ),
            "optimum_cost": optimum,
            "optimum_assignments": assignments,
        }

    uniform_cost = weighted_optima(
        evaluator, INITIAL_SCENARIO_WEIGHTS, "cost", joint_feasible=True
    )
    uniform_regret = weighted_optima(
        evaluator, INITIAL_SCENARIO_WEIGHTS, "regret", joint_feasible=True
    )
    minimax = minimax_regret_optima(evaluator)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plan_version": PLAN_VERSION,
        "assignment_count": len(all_assignments()),
        "joint_feasible_count": len(evaluator.joint_feasible_assignments()),
        "scenarios": scenario_results,
        "uniform_joint_cost": {
            "value": uniform_cost[0],
            "assignments": uniform_cost[1],
        },
        "uniform_joint_regret": {
            "value": uniform_regret[0],
            "assignments": uniform_regret[1],
        },
        "pure_minimax_regret": {
            "value": minimax[0],
            "assignments": minimax[1],
        },
        "adaptive_cost": exact_adaptive_run(evaluator, "cost"),
        "adaptive_regret": exact_adaptive_run(evaluator, "regret"),
        "implementation_findings": [
            "The frozen plan lists one minimax representative; exhaustive enumeration finds a symmetric two-way tie."
        ],
    }
    output = write_json(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "tables"
        / "exact_truth.json",
        payload,
    )
    print(output)


if __name__ == "__main__":
    main()
