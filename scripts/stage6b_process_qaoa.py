"""Post-process saved Stage 6B samples; never execute quantum circuits."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path

import pandas as pd

from qera.config import FINAL_SHOTS
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance, generate_instance
from qera_scaling.qubo import build_energy_spec
from qera_stage6b.postprocess import (
    MATCHED_BATCHES,
    WEIGHTS,
    every_seed_passes_quality_gate,
    exact_uniform_valid_metrics,
    matched_control_summary,
    matched_uniform_valid_batches,
    process_saved_frame,
)
from qera_stage6b.provenance import sha256_file


D4_SEEDS = (6601, 6602, 6603)
D6_SEEDS = (6611, 6612, 6613)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, choices=(4, 6), required=True)
    return parser.parse_args()


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts" / "stage6b"
    table_dir = artifacts / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    results_path = table_dir / f"stage6b_d{args.D}_results.csv"
    seed_summary_path = table_dir / f"stage6b_d{args.D}_seed_summary.csv"
    aggregate_path = artifacts / f"d{args.D}" / "aggregate_summary.json"
    for path in (results_path, seed_summary_path, aggregate_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite Stage 6B evidence: {path}")

    seeds = D4_SEEDS if args.D == 4 else D6_SEEDS
    instance = frozen_instance() if args.D == 4 else generate_instance(args.D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    population = exact_uniform_valid_metrics(evaluator)
    results = []
    seed_summaries = []
    failed_seeds = []
    for seed in seeds:
        run_dir = artifacts / f"d{args.D}" / "runs" / f"seed-{seed}"
        manifest_path = run_dir / "manifest.json"
        manifest = _load_manifest(manifest_path)
        if manifest["status"] != "RAW_SAMPLE_SAVED":
            failed_seeds.append(seed)
            results.append(
                {
                    "D": args.D,
                    "method": "constrained_qaoa_p1",
                    "seed": seed,
                    "status": manifest["status"],
                }
            )
            continue
        raw_path = run_dir / "samples_raw.csv"
        if manifest["samples_raw_sha256"] != sha256_file(raw_path):
            raise ValueError(f"raw sample hash mismatch for seed {seed}")
        processed, raw_summary, metrics = process_saved_frame(
            pd.read_csv(raw_path),
            evaluator,
            spec,
            FINAL_SHOTS,
        )
        processed_path = run_dir / "samples_processed.csv"
        summary_path = run_dir / "summary.json"
        if processed_path.exists() or summary_path.exists():
            raise FileExistsError(f"refusing to overwrite processed seed {seed}")
        processed.to_csv(processed_path, index=False)
        combined_summary = {
            "schema_version": "stage6b-1.0",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "D": args.D,
            "seed": seed,
            "status": "PROCESSED",
            "raw_summary": raw_summary,
            "distribution_metrics": metrics,
            "samples_raw_sha256": sha256_file(raw_path),
            "samples_processed_sha256": sha256_file(processed_path),
        }
        summary_path.write_text(
            json.dumps(combined_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        matched = matched_uniform_valid_batches(
            evaluator,
            int(metrics["one_hot_count"]),
            seed=7600 + seed,
            batches=MATCHED_BATCHES,
        )
        matched_path = run_dir / "matched_uniform_valid_batches.csv"
        pd.DataFrame(matched).to_csv(matched_path, index=False)
        comparison = matched_control_summary(metrics, matched)
        results.append(
            {
                "D": args.D,
                "method": "constrained_qaoa_p1",
                "seed": seed,
                "status": "SUCCESS",
                **metrics,
                "execution_runtime_seconds": manifest["execution_runtime_seconds"],
                "optimizer_trace_length": manifest["optimizer_trace_length"],
                "best_gamma": manifest["best_parameters"]["params"][0],
                "best_beta": manifest["best_parameters"]["params"][1],
            }
        )
        seed_summaries.append(
            {
                "D": args.D,
                "seed": seed,
                "matched_control_seed": 7600 + seed,
                **comparison,
                "matched_batches_sha256": sha256_file(matched_path),
            }
        )

    results.append(
        {
            "D": args.D,
            "method": "uniform_valid_exact_population",
            "seed": None,
            "status": "REFERENCE",
            "total_shots": None,
            "one_hot_count": None,
            "one_hot_probability": 1.0,
            "joint_feasible_count": population["joint_feasible_count"],
            "joint_feasible_probability": population["feasible_fraction_valid"],
            "feasible_fraction_valid": population["feasible_fraction_valid"],
            "near_optimal_count": population["near_optimal_count"],
            "near_optimal_probability": population["near_optimal_fraction_valid"],
            "near_optimal_fraction_valid": population["near_optimal_fraction_valid"],
            "exact_optimum_count": population["exact_optimum_count"],
            "exact_optimum_probability": population["exact_optimum_fraction_valid"],
            "exact_optimum_fraction_valid": population["exact_optimum_fraction_valid"],
            "mean_valid_objective": population["mean_valid_objective"],
            "q25_valid_objective": population["q25_valid_objective"],
            "median_valid_objective": population["median_valid_objective"],
            "q75_valid_objective": population["q75_valid_objective"],
            "best_feasible_objective_gap": population["best_feasible_objective_gap"],
            "best_feasible_worst_case_regret": population[
                "best_feasible_worst_case_regret"
            ],
        }
    )

    if args.D == 4:
        x_run = root / "artifacts" / "runs" / "uniform_cost_p1_smoke"
        x_processed, _, x_metrics = process_saved_frame(
            pd.read_csv(x_run / "samples_raw.csv"),
            evaluator,
            spec,
            FINAL_SHOTS,
        )
        results.append(
            {
                "D": 4,
                "method": "existing_x_mixer_qaoa_p1",
                "seed": 7,
                "status": "FROZEN_REFERENCE",
                **x_metrics,
            }
        )

    result_frame = pd.DataFrame(results)
    seed_frame = pd.DataFrame(seed_summaries)
    result_frame.to_csv(results_path, index=False)
    seed_frame.to_csv(seed_summary_path, index=False)
    qaoa = result_frame[result_frame["method"] == "constrained_qaoa_p1"]
    successful = qaoa[qaoa["status"] == "SUCCESS"]
    aggregate_metrics = {}
    for metric in (
        "one_hot_probability",
        "joint_feasible_probability",
        "near_optimal_probability",
        "exact_optimum_probability",
        "mean_valid_objective",
        "median_valid_objective",
        "best_feasible_objective_gap",
        "best_feasible_worst_case_regret",
    ):
        values = successful[metric].dropna()
        aggregate_metrics[metric] = {
            "mean": float(values.mean()),
            "std_across_seeds": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "min": float(values.min()),
            "max": float(values.max()),
        }
    mean_pvalues = seed_frame[
        "empirical_p_random_at_least_as_good_mean_valid_objective"
    ] if not seed_frame.empty else pd.Series(dtype=float)
    near_pvalues = seed_frame[
        "empirical_p_random_at_least_as_good_near_optimal_fraction_valid"
    ] if not seed_frame.empty else pd.Series(dtype=float)
    d6_gate = (
        args.D == 4
        and not failed_seeds
        and len(successful) == len(seeds)
        and bool((successful["one_hot_probability"] == 1.0).all())
        and bool((successful["total_shots"] == FINAL_SHOTS).all())
        and every_seed_passes_quality_gate(
            mean_pvalues.tolist(),
            near_pvalues.tolist(),
        )
    )
    aggregate = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "D": args.D,
        "predeclared_seeds": seeds,
        "successful_seeds": [int(seed) for seed in successful["seed"]],
        "failed_seeds": failed_seeds,
        "uniform_valid_population": population,
        "aggregate_metrics": aggregate_metrics,
        "d6_gate_applicable": args.D == 4,
        "d6_gate_rule": (
            "all three executions succeed with 4096 one-hot shots and every seed "
            "beats at least 95% of matched uniform-valid batches on either mean "
            "objective or near-optimal fraction"
            if args.D == 4
            else None
        ),
        "d6_gate_passed": d6_gate if args.D == 4 else None,
        "results_sha256": sha256_file(results_path),
        "seed_summary_sha256": sha256_file(seed_summary_path),
    }
    aggregate_path.write_text(
        json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(results_path.resolve())
    print(seed_summary_path.resolve())
    print(aggregate_path.resolve())
    print(json.dumps(aggregate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
