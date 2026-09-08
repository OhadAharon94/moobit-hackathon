"""Generate Stage 4 exact, heuristic, and matched random controls."""

from __future__ import annotations

import json
from pathlib import Path

from qera.baselines import (
    load_aware_greedy,
    random_bitstring_frame,
    random_valid_route_frame,
    shortest_path_assignment,
)
from qera.classiq_solver import process_sample_frame
from qera.config import DEFAULT_SEED, FINAL_SHOTS, INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.exact import minimax_regret_optima, weighted_optima
from qera.instance import SCENARIOS
from qera.records import write_json


def assignment_metrics(evaluator: Evaluator, assignment) -> dict:
    evaluations = evaluator.evaluate_all(assignment)
    return {
        "assignment": assignment,
        "joint_feasible": all(item.feasible for item in evaluations),
        "total_overflow": sum(item.overflow for item in evaluations),
        "maximum_utilization": max(item.maximum_utilization for item in evaluations),
        "scenario_costs": {item.scenario: item.cost for item in evaluations},
        "scenario_regrets": {
            scenario.name: evaluator.regret(assignment, scenario)
            for scenario in SCENARIOS
        },
    }


def main() -> None:
    evaluator = Evaluator()
    controls = {
        "shortest_path": assignment_metrics(evaluator, shortest_path_assignment()),
        "load_aware_greedy_all_training_scenarios": assignment_metrics(
            evaluator, load_aware_greedy(evaluator)
        ),
    }
    for mode in ("cost", "regret"):
        unrestricted = weighted_optima(
            evaluator, INITIAL_SCENARIO_WEIGHTS, mode, joint_feasible=False
        )
        joint = weighted_optima(
            evaluator, INITIAL_SCENARIO_WEIGHTS, mode, joint_feasible=True
        )
        controls[f"exact_unrestricted_uniform_{mode}"] = {
            "value": unrestricted[0],
            "assignments": unrestricted[1],
        }
        controls[f"exact_joint_uniform_{mode}"] = {
            "value": joint[0],
            "assignments": joint[1],
        }
    minimax = minimax_regret_optima(evaluator)
    controls["exact_pure_minimax_regret"] = {
        "value": minimax[0],
        "assignments": minimax[1],
    }

    random_summaries = {}
    for name, frame in (
        ("uniform_random_bitstrings", random_bitstring_frame(FINAL_SHOTS, DEFAULT_SEED)),
        ("uniform_random_valid_routes", random_valid_route_frame(FINAL_SHOTS, DEFAULT_SEED)),
    ):
        spec = build_energy_spec(
            evaluator, INITIAL_SCENARIO_WEIGHTS, "cost", energy_mode="base"
        )
        processed, summary = process_sample_frame(
            frame,
            evaluator,
            spec,
            INITIAL_SCENARIO_WEIGHTS,
            "cost",
            declared_shots=FINAL_SHOTS,
        )
        processed.to_csv(
            Path(__file__).resolve().parents[1]
            / "artifacts"
            / "tables"
            / f"{name}.csv",
            index=False,
        )
        random_summaries[name] = summary

    output = write_json(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "tables"
        / "static_controls.json",
        {"controls": controls, "random_controls": random_summaries},
    )
    print(output)
    print(json.dumps({"controls": controls, "random_controls": random_summaries}, indent=2, default=list))


if __name__ == "__main__":
    main()
