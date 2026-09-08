"""Run the frozen classical-only evolution ablation and validation-first selection."""

from __future__ import annotations

import json
from dataclasses import asdict
from math import isclose
from pathlib import Path

from holy_qow_evolution.audit import global_update_audit, verify_run
from holy_qow_evolution.common import artifact_root, sha256_file, write_csv, write_json
from holy_qow_evolution.engine import EvolutionRun, run_adaptive_exact
from holy_qow_evolution.metrics import evaluate_route
from holy_qow_evolution.scenarios import final_test_pool, training_pool, validation_pool


def compact_metrics(metrics: dict, prefix: str) -> dict:
    return {
        f"{prefix}_{key}": value
        for key, value in metrics.items()
        if key != "rows"
    }


def route_json(route: tuple[int, ...]) -> str:
    return json.dumps(route, separators=(",", ":"))


def run_payload(run_id: str, run: EvolutionRun) -> dict:
    return {
        "schema_version": "holy-qow-evolution-run-v1",
        "run_id": run_id,
        "solver": "exact exhaustive classical best response",
        "objective": "weighted normalized cost",
        "eta": run.eta,
        "T": run.iterations,
        "rho": run.rho,
        "scenario_ids": run.scenario_ids,
        "steps": [asdict(step) for step in run.steps],
        "final_assignment": run.final_assignment,
        "final_weights": run.final_weights,
    }


def selection_key(row: dict) -> tuple:
    return (
        -float(row["validation_survival_rate"]),
        float(row["validation_maximum_overflow"]),
        float(row["validation_worst_regret"]),
        float(row["validation_mean_regret"]),
        float(row["validation_nominal_cost"]),
        int(row["S"]),
        float(row["eta"]),
        int(row["T"]),
        float(row["rho"]),
        str(row["run_id"]),
    )


def run_one(config: dict, training: tuple, validation_cache: dict) -> tuple[EvolutionRun, dict, list[dict], list[dict]]:
    scenarios = training[: int(config["S"])]
    run = run_adaptive_exact(
        scenarios,
        eta=float(config["eta"]),
        iterations=int(config["T"]),
        rho=float(config["rho"]),
    )
    audit = verify_run(run, scenarios)
    if not all(audit.values()):
        raise AssertionError(f"correctness gate failed for {config['run_id']}")
    route = run.final_assignment
    training_metrics = evaluate_route(route, scenarios)
    if route not in validation_cache:
        validation_cache[route] = evaluate_route(route, validation_pool())
    validation_metrics = validation_cache[route]
    summary = {
        **config,
        "final_assignment": route_json(route),
        "trajectory_distinct_routes": len({step.assignment for step in run.steps}),
        "final_weight_entropy": run.steps[-1].entropy,
        "final_effective_environments": run.steps[-1].effective_environments,
        "final_effective_fraction": run.steps[-1].effective_environments / int(config["S"]),
        "final_maximum_weight": max(run.final_weights),
        "minimum_effective_environments": min(step.effective_environments for step in run.steps),
        "all_exact_best_response_checks_pass": all(audit.values()),
        **compact_metrics(training_metrics, "training"),
        **compact_metrics(validation_metrics, "validation"),
    }
    trajectories = []
    for step in run.steps:
        trajectories.append(
            {
                "run_id": config["run_id"],
                "run_family": config["run_family"],
                "S": config["S"],
                "eta": config["eta"],
                "T": config["T"],
                "rho": config["rho"],
                "iteration": step.iteration,
                "assignment": route_json(step.assignment),
                "all_tied_optima": json.dumps(step.tied_optima, separators=(",", ":")),
                "tie_count": len(step.tied_optima),
                "objective_value": step.objective_value,
                "weights": json.dumps(step.weights, separators=(",", ":")),
                "regrets": json.dumps(step.regrets, separators=(",", ":")),
                "clipped_regrets": json.dumps(step.clipped_regrets, separators=(",", ":")),
                "pre_mixing_weights": json.dumps(step.pre_mixing_weights, separators=(",", ":")) if step.pre_mixing_weights is not None else "",
                "next_weights": json.dumps(step.next_weights, separators=(",", ":")) if step.next_weights is not None else "",
                "weight_entropy": step.entropy,
                "effective_environments": step.effective_environments,
                "effective_fraction": step.effective_environments / int(config["S"]),
            }
        )
    validation_rows = [
        {
            "run_id": config["run_id"],
            "S": config["S"],
            "eta": config["eta"],
            "T": config["T"],
            "rho": config["rho"],
            "assignment": route_json(route),
            **row,
        }
        for row in validation_metrics["rows"]
    ]
    return run, summary, trajectories, validation_rows


def main() -> None:
    out = artifact_root()
    manifests = out / "manifests"
    freeze_path = manifests / "freeze_record.json"
    scenario_path = manifests / "evolution_scenario_manifests.json"
    design_path = manifests / "predeclared_experiment_grid.json"
    b0_path = manifests / "b0_reproduction.json"
    for path in (freeze_path, scenario_path, design_path, b0_path):
        if not path.is_file():
            raise FileNotFoundError(f"required frozen gate artifact is missing: {path}")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze["scenario_manifest_sha256"] != sha256_file(scenario_path):
        raise ValueError("scenario manifest changed after freeze")
    if freeze["experiment_grid_sha256"] != sha256_file(design_path):
        raise ValueError("experiment grid changed after freeze")
    if json.loads(b0_path.read_text(encoding="utf-8"))["status"] != "PASS":
        raise ValueError("B0 did not pass")
    design = json.loads(design_path.read_text(encoding="utf-8"))
    configs = design["configurations"]
    training = training_pool()
    validation = validation_pool()
    if len(configs) != design["config_count"]:
        raise ValueError("predeclared config count mismatch")

    runs_dir = out / "runs"
    validation_cache: dict = {}
    summaries: list[dict] = []
    trajectory_rows: list[dict] = []
    validation_rows: list[dict] = []
    run_hashes = {}
    full_audit = global_update_audit(training[:5])
    if full_audit["status"] != "PASS":
        write_json(manifests / "weight_update_correctness.json", full_audit)
        raise AssertionError("global weight-update audit failed")
    for index, config in enumerate(configs, start=1):
        run, summary, trajectories, per_scenario = run_one(config, training, validation_cache)
        raw_target = runs_dir / f"{config['run_id']}.json"
        payload = run_payload(config["run_id"], run)
        if raw_target.exists():
            if json.loads(raw_target.read_text(encoding="utf-8")) != json.loads(
                json.dumps(payload, allow_nan=False)
            ):
                raise ValueError(f"existing raw run differs from deterministic replay: {raw_target}")
            raw_path = raw_target.resolve()
        else:
            raw_path = write_json(raw_target, payload)
        run_hashes[config["run_id"]] = sha256_file(raw_path)
        summaries.append(summary)
        trajectory_rows.extend(trajectories)
        validation_rows.extend(per_scenario)
        if index % 32 == 0:
            print(f"completed {index}/{len(configs)} exact runs")
    write_json(manifests / "weight_update_correctness.json", full_audit)
    tables = out / "tables"
    validation_summary_path = write_csv(tables / "evolution_validation_results.csv", summaries)
    trajectories_path = write_csv(tables / "evolution_weight_trajectories.csv", trajectory_rows)
    validation_rows_path = write_csv(tables / "evolution_validation_scenario_results.csv", validation_rows)

    adaptive_candidates = [row for row in summaries if float(row["eta"]) > 0.0]
    static_candidates = [row for row in summaries if isclose(float(row["eta"]), 0.0)]
    selected_adaptive = min(adaptive_candidates, key=selection_key)
    selected_static = min(static_candidates, key=selection_key)
    original_static = next(
        row
        for row in summaries
        if row["run_family"] == "B4-focused"
        and row["S"] == 3
        and isclose(row["eta"], 0.0)
        and row["T"] == 3
        and isclose(row["rho"], 0.0)
    )
    selection = {
        "schema_version": "holy-qow-evolution-selection-v1",
        "status": "FROZEN_BEFORE_FINAL_TEST_EVALUATION",
        "validation_summary_sha256": sha256_file(validation_summary_path),
        "selection_rule": design["validation_selection_rule"],
        "selected_adaptive_run_id": selected_adaptive["run_id"],
        "selected_adaptive_assignment": selected_adaptive["final_assignment"],
        "selected_static_uniform_run_id": selected_static["run_id"],
        "selected_static_uniform_assignment": selected_static["final_assignment"],
        "original_s3_static_run_id": original_static["run_id"],
        "original_s3_static_assignment": original_static["final_assignment"],
        "final_test_consulted_for_selection": False,
    }
    selection_path = write_json(manifests / "selection_before_final.json", selection)

    final = final_test_pool()
    final_cache: dict = {}
    grid_rows: list[dict] = []
    final_scenario_rows: list[dict] = []
    for summary in summaries:
        route = tuple(json.loads(summary["final_assignment"]))
        if route not in final_cache:
            final_cache[route] = evaluate_route(route, final)
        final_metrics = final_cache[route]
        row = {
            **summary,
            **compact_metrics(final_metrics, "final"),
            "selected_adaptive_on_validation": summary["run_id"] == selection["selected_adaptive_run_id"],
            "selected_static_on_validation": summary["run_id"] == selection["selected_static_uniform_run_id"],
            "original_s3_static_control": summary["run_id"] == selection["original_s3_static_run_id"],
        }
        grid_rows.append(row)
        final_scenario_rows.extend(
            {
                "run_id": summary["run_id"],
                "S": summary["S"],
                "eta": summary["eta"],
                "T": summary["T"],
                "rho": summary["rho"],
                "assignment": summary["final_assignment"],
                **item,
            }
            for item in final_metrics["rows"]
        )
    grid_path = write_csv(tables / "evolution_grid_results.csv", grid_rows)
    final_rows_path = write_csv(tables / "evolution_final_scenario_results.csv", final_scenario_rows)
    evidence_manifest = {
        "schema_version": "holy-qow-evolution-evidence-v1",
        "status": "COMPLETE",
        "solver": "exact exhaustive classical only; no quantum execution",
        "scenario_manifest_sha256": sha256_file(scenario_path),
        "experiment_grid_sha256": sha256_file(design_path),
        "selection_before_final_sha256": sha256_file(selection_path),
        "raw_run_count": len(run_hashes),
        "raw_run_sha256": run_hashes,
        "outputs": {
            "evolution_grid_results.csv": sha256_file(grid_path),
            "evolution_weight_trajectories.csv": sha256_file(trajectories_path),
            "evolution_validation_scenario_results.csv": sha256_file(validation_rows_path),
            "evolution_final_scenario_results.csv": sha256_file(final_rows_path),
        },
        "negative_runs_retained": True,
        "final_test_used_for_selection": False,
    }
    write_json(manifests / "evidence_manifest.json", evidence_manifest)
    print(json.dumps(selection, indent=2, sort_keys=True))
    print(grid_path)


if __name__ == "__main__":
    main()
