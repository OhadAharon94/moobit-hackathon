"""Evaluate frozen routes on the already-frozen held-out scenario manifest."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance

from holy_qow_post6a.common import artifact_root, sha256_file, write_csv, write_json
from holy_qow_post6a.heldout import build_evaluator, heldout_scenarios


def main() -> None:
    output = artifact_root() / "heldout"
    scenario_path = output / "heldout_scenario_manifest.json"
    route_path = output / "heldout_route_manifest.json"
    freeze_path = output / "freeze_record.json"
    for path in (scenario_path, route_path, freeze_path):
        if not path.is_file():
            raise FileNotFoundError("freeze Step 1 manifests before evaluating routes")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["scenario_manifest_sha256"] != sha256_file(scenario_path):
        raise ValueError("held-out scenario manifest changed after freeze")
    if freeze["route_manifest_sha256"] != sha256_file(route_path):
        raise ValueError("held-out route manifest changed after freeze")
    manifest = json.loads(scenario_path.read_text(encoding="utf-8"))
    route_data = json.loads(route_path.read_text(encoding="utf-8"))
    specs = {spec.scenario_id: spec for spec in heldout_scenarios()}
    if tuple(item["scenario_id"] for item in manifest["scenarios"]) != tuple(specs):
        raise ValueError("held-out generator no longer matches the frozen manifest")

    result_rows = []
    for scenario_record in manifest["scenarios"]:
        scenario_id = scenario_record["scenario_id"]
        evaluator = build_evaluator(specs[scenario_id])
        exact_value, exact_routes, _ = evaluator.exact_optima(
            (1.0, 0.0, 0.0), "cost", joint_feasible=True
        )
        scenario_rows = []
        for route_record in route_data["routes"]:
            assignment = tuple(route_record["assignment"])
            evaluation = evaluator.evaluate(assignment, "nominal")
            row = {
                "scenario_id": scenario_id,
                "category": scenario_record["category"],
                "route_id": route_record["route_id"],
                "assignment": json.dumps(route_record["assignment"]),
                "normalized_cost": evaluation.cost,
                "regret": evaluator.regret(assignment, "nominal"),
                "feasible": evaluation.feasible,
                "overflow": evaluation.overflow,
                "maximum_utilization": evaluation.maximum_utilization,
                "weighted_latency": evaluation.latency,
                "exact_feasible_optimum": exact_value,
                "exact_optimum_assignments": json.dumps(exact_routes),
            }
            scenario_rows.append(row)
        viable = [row for row in scenario_rows if row["feasible"]]
        candidates = viable or scenario_rows
        winning_regret = min(row["regret"] for row in candidates)
        winners = {
            row["route_id"]
            for row in candidates
            if abs(row["regret"] - winning_regret) <= 1e-12
        }
        for row in scenario_rows:
            row["scenario_winner"] = row["route_id"] in winners
            row["fractional_win"] = 1.0 / len(winners) if row["route_id"] in winners else 0.0
            result_rows.append(row)

    base_evaluator = ScalingEvaluator(frozen_instance())
    summary_rows = []
    for route_record in route_data["routes"]:
        route_id = route_record["route_id"]
        values = [row for row in result_rows if row["route_id"] == route_id]
        assignment = tuple(route_record["assignment"])
        training_nominal = base_evaluator.evaluate(assignment, "nominal")
        summary_rows.append(
            {
                "route_id": route_id,
                "assignment": json.dumps(route_record["assignment"]),
                "scenario_count": len(values),
                "mean_normalized_cost": sum(row["normalized_cost"] for row in values) / len(values),
                "median_normalized_cost": median(row["normalized_cost"] for row in values),
                "mean_regret": sum(row["regret"] for row in values) / len(values),
                "median_regret": median(row["regret"] for row in values),
                "worst_case_regret": max(row["regret"] for row in values),
                "survival_rate": sum(row["feasible"] for row in values) / len(values),
                "violating_scenarios": sum(not row["feasible"] for row in values),
                "mean_overflow": sum(row["overflow"] for row in values) / len(values),
                "maximum_overflow": max(row["overflow"] for row in values),
                "mean_maximum_utilization": sum(row["maximum_utilization"] for row in values) / len(values),
                "worst_maximum_utilization": max(row["maximum_utilization"] for row in values),
                "mean_weighted_latency": sum(row["weighted_latency"] for row in values) / len(values),
                "maximum_weighted_latency": max(row["weighted_latency"] for row in values),
                "scenario_wins_including_ties": sum(row["scenario_winner"] for row in values),
                "fractional_scenario_wins": sum(row["fractional_win"] for row in values),
                "training_nominal_cost": training_nominal.cost,
                "training_nominal_feasible": training_nominal.feasible,
            }
        )
    results_path = write_csv(output / "heldout_route_results.csv", result_rows)
    summary_path = write_csv(output / "heldout_route_summary.csv", summary_rows)
    evaluation_manifest = {
        "schema_version": "post6a-steps0-2-v1",
        "step": 1,
        "status": "COMPLETE",
        "scenario_manifest_sha256": sha256_file(scenario_path),
        "route_manifest_sha256": sha256_file(route_path),
        "evaluator": "qera_scaling.evaluate.ScalingEvaluator using the frozen D=4 fixture",
        "normalization": "per-held-out-scenario over all 81 structurally valid routes",
        "regret_reference": "per-held-out-scenario feasible optimum and feasible maximum",
        "route_training_or_tuning_after_freeze": False,
        "outputs": {
            "heldout_route_results_sha256": sha256_file(results_path),
            "heldout_route_summary_sha256": sha256_file(summary_path),
        },
    }
    write_json(output / "evaluation_manifest.json", evaluation_manifest)
    print(results_path)
    print(summary_path)
    print(json.dumps(summary_rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
