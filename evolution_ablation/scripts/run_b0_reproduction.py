"""B0 gate: reproduce frozen exact adaptation and held-out metrics before ablation."""

from __future__ import annotations

import csv
import json
from math import isclose

from qera.evaluate import Evaluator
from qera.exact import exact_adaptive_run

from holy_qow_evolution.common import artifact_root, implementation_root, sha256_file, write_json
from holy_qow_evolution.metrics import evaluate_route
from holy_qow_evolution.scenarios import final_test_pool, original_training_pool
from holy_qow_evolution.engine import run_adaptive_exact


def close(a: float, b: float) -> bool:
    return isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-12)


def main() -> None:
    root = implementation_root()
    truth_path = root / "artifacts" / "tables" / "exact_truth.json"
    heldout_path = root / "artifacts" / "post6a" / "heldout" / "heldout_route_summary.csv"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    expected = truth["adaptive_cost"]

    frozen = exact_adaptive_run(Evaluator(), "cost")
    reproduced = run_adaptive_exact(original_training_pool(), eta=1.0, iterations=3, rho=0.0)
    checks: dict[str, bool] = {}
    checks["frozen_qera_length"] = len(frozen) == len(expected)
    checks["new_engine_length"] = len(reproduced.steps) == len(expected)
    for index, expected_step in enumerate(expected):
        frozen_step = frozen[index]
        new_step = reproduced.steps[index]
        checks[f"frozen_route_t{index}"] = list(frozen_step.assignment) == expected_step["assignment"]
        checks[f"new_route_t{index}"] = list(new_step.assignment) == expected_step["assignment"]
        checks[f"frozen_weights_t{index}"] = all(close(a, b) for a, b in zip(frozen_step.weights, expected_step["weights"], strict=True))
        checks[f"new_weights_t{index}"] = all(close(a, b) for a, b in zip(new_step.weights, expected_step["weights"], strict=True))
        checks[f"new_regrets_t{index}"] = all(close(a, b) for a, b in zip(new_step.regrets, expected_step["regrets"], strict=True))
        checks[f"new_objective_t{index}"] = close(new_step.objective_value, expected_step["objective_value"])

    metrics = evaluate_route(reproduced.final_assignment, final_test_pool())
    with heldout_path.open(newline="", encoding="utf-8") as handle:
        published = next(row for row in csv.DictReader(handle) if row["route_id"] == "exact_adaptive")
    metric_map = {
        "mean_cost": "mean_normalized_cost",
        "median_cost": "median_normalized_cost",
        "mean_regret": "mean_regret",
        "median_regret": "median_regret",
        "worst_regret": "worst_case_regret",
        "survival_rate": "survival_rate",
        "mean_overflow": "mean_overflow",
        "maximum_overflow": "maximum_overflow",
        "mean_maximum_utilization": "mean_maximum_utilization",
        "worst_maximum_utilization": "worst_maximum_utilization",
        "mean_weighted_latency": "mean_weighted_latency",
        "maximum_weighted_latency": "maximum_weighted_latency",
        "nominal_cost": "training_nominal_cost",
    }
    for actual_name, published_name in metric_map.items():
        checks[f"heldout_{actual_name}"] = close(metrics[actual_name], float(published[published_name]))
    checks["heldout_violations"] = metrics["violating_scenarios"] == int(published["violating_scenarios"])
    checks["heldout_scenario_count"] = metrics["scenario_count"] == int(published["scenario_count"])

    status = "PASS" if all(checks.values()) else "FAIL"
    record = {
        "schema_version": "holy-qow-evolution-b0-v1",
        "status": status,
        "checks": checks,
        "expected_trajectory": expected,
        "reproduced_trajectory": [
            {
                "iteration": step.iteration,
                "weights": step.weights,
                "assignment": step.assignment,
                "all_tied_optima": step.tied_optima,
                "objective_value": step.objective_value,
                "regrets": step.regrets,
            }
            for step in reproduced.steps
        ],
        "heldout_metrics": {key: value for key, value in metrics.items() if key != "rows"},
        "source_hashes": {
            "exact_truth.json": sha256_file(truth_path),
            "heldout_route_summary.csv": sha256_file(heldout_path),
        },
    }
    path = write_json(artifact_root() / "manifests" / "b0_reproduction.json", record)
    print(path)
    print(json.dumps({"status": status, "failed_checks": [key for key, value in checks.items() if not value]}, indent=2))
    if status != "PASS":
        raise SystemExit("B0 reproduction failed; ablation is forbidden")


if __name__ == "__main__":
    main()
