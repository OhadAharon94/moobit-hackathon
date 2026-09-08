"""Freeze Stage 6B statistics, the D=6 gate decision, and saved-data figures."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance
from qera_stage6b.postprocess import WEIGHTS
from qera_stage6b.provenance import sha256_file


def _weighted_values(frame: pd.DataFrame) -> np.ndarray:
    return np.repeat(
        frame["weighted_cost"].astype(float).to_numpy(),
        frame["counts"].astype(int).to_numpy(),
    )


def _save_figure(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts" / "stage6b"
    figure_dir = artifacts / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    statistics_path = artifacts / "d4" / "statistical_summary.json"
    d6_gate_path = artifacts / "d6" / "gate_decision.json"
    figure_manifest_path = figure_dir / "manifest.json"
    for path in (statistics_path, d6_gate_path, figure_manifest_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite Stage 6B evidence: {path}")
    d6_gate_path.parent.mkdir(parents=True, exist_ok=True)

    results = pd.read_csv(artifacts / "tables" / "stage6b_d4_results.csv")
    seed_summary = pd.read_csv(
        artifacts / "tables" / "stage6b_d4_seed_summary.csv"
    )
    aggregate = json.loads(
        (artifacts / "d4" / "aggregate_summary.json").read_text(encoding="utf-8")
    )
    qaoa = results[results["method"] == "constrained_qaoa_p1"].copy()
    uniform = results[results["method"] == "uniform_valid_exact_population"].iloc[0]
    test = ttest_1samp(
        qaoa["mean_valid_objective"].astype(float),
        float(uniform["mean_valid_objective"]),
        alternative="less",
    )
    mean_improvement = (
        float(uniform["mean_valid_objective"])
        - float(qaoa["mean_valid_objective"].mean())
    )
    statistics = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "D": 4,
        "seed_count": len(qaoa),
        "mean_qaoa_valid_objective": float(qaoa["mean_valid_objective"].mean()),
        "std_qaoa_valid_objective_across_seeds": float(
            qaoa["mean_valid_objective"].std(ddof=1)
        ),
        "uniform_valid_population_mean_objective": float(
            uniform["mean_valid_objective"]
        ),
        "absolute_mean_objective_improvement": mean_improvement,
        "relative_mean_objective_improvement": mean_improvement
        / float(uniform["mean_valid_objective"]),
        "exploratory_one_sample_t_test": {
            "alternative": "QAOA seed mean objective is lower than uniform-valid population mean",
            "statistic": float(test.statistic),
            "p_value": float(test.pvalue),
            "degrees_of_freedom": int(test.df),
            "caution": "Only three optimizer seeds; this test is descriptive, not secure evidence.",
        },
        "matched_seed_mean_objective_p_values": [
            float(value)
            for value in seed_summary[
                "empirical_p_random_at_least_as_good_mean_valid_objective"
            ]
        ],
        "matched_seed_near_optimal_p_values": [
            float(value)
            for value in seed_summary[
                "empirical_p_random_at_least_as_good_near_optimal_fraction_valid"
            ]
        ],
        "interpretation": (
            "Two seeds shifted the overall mean cost downward, but one did not; "
            "near-optimal, exact-optimum, and feasible mass were below uniform-valid "
            "sampling in all three seeds. Optimization superiority is not reproducible."
        ),
    }
    statistics_path.write_text(
        json.dumps(statistics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    d6_gate = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "NOT_ATTEMPTED",
        "gate_passed": False,
        "decision": "STOP_AT_D4",
        "gate_rule": aggregate["d6_gate_rule"],
        "reason": (
            "Correctness and execution stability passed, but every-seed matched-valid "
            "quality reproducibility did not. Seed 6602 failed the mean-objective "
            "criterion and all seeds had worse near-optimal mass than uniform-valid."
        ),
        "prohibited_actions_respected": [
            "no D=6 synthesis",
            "no D=6 quantum execution",
            "no adaptive scenario reweighting",
            "no combined adaptive-constrained algorithm",
        ],
        "d4_aggregate_sha256": sha256_file(
            artifacts / "d4" / "aggregate_summary.json"
        ),
        "d4_statistics_sha256": sha256_file(statistics_path),
    }
    d6_gate_path.write_text(
        json.dumps(d6_gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    evaluator = ScalingEvaluator(frozen_instance())
    uniform_costs = sorted(
        evaluator.weighted_objective(route, WEIGHTS, "cost")
        for route in evaluator.all_assignments()
    )
    plt.figure(figsize=(8, 5))
    x = np.asarray(uniform_costs)
    plt.step(x, np.arange(1, len(x) + 1) / len(x), where="post", label="Uniform-valid population", linewidth=2)
    for seed in (6601, 6602, 6603):
        processed = pd.read_csv(
            artifacts / "d4" / "runs" / f"seed-{seed}" / "samples_processed.csv"
        )
        values = np.sort(_weighted_values(processed[processed["one_hot"]]))
        plt.step(
            values,
            np.arange(1, len(values) + 1) / len(values),
            where="post",
            label=f"Constrained QAOA {seed}",
            alpha=0.85,
        )
    plt.xlabel("Frozen weighted objective (lower is better)")
    plt.ylabel("Empirical cumulative probability")
    plt.title("D=4 valid-route cost distributions")
    plt.legend(fontsize=8)
    plt.grid(alpha=0.25)
    _save_figure(figure_dir / "01_d4_cost_ecdf.png")

    plt.figure(figsize=(8, 5))
    seeds = seed_summary["seed"].astype(int).astype(str)
    observed = seed_summary["qaoa_mean_valid_objective"].astype(float)
    control_mean = seed_summary["random_mean_valid_objective_mean"].astype(float)
    control_low = seed_summary["random_mean_valid_objective_q25"].astype(float)
    control_high = seed_summary["random_mean_valid_objective_q75"].astype(float)
    positions = np.arange(len(seeds))
    plt.errorbar(
        positions,
        control_mean,
        yerr=[control_mean - control_low, control_high - control_mean],
        fmt="o",
        capsize=5,
        label="Matched uniform-valid mean and IQR",
    )
    plt.scatter(positions, observed, marker="D", s=65, label="Constrained QAOA")
    plt.xticks(positions, seeds)
    plt.xlabel("Optimizer seed")
    plt.ylabel("Mean valid-route objective")
    plt.title("D=4 matched valid-budget comparison")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    _save_figure(figure_dir / "02_d4_matched_valid_means.png")

    probability_metrics = [
        ("feasible_fraction_valid", "Feasible"),
        ("near_optimal_fraction_valid", "Near-optimal"),
        ("exact_optimum_fraction_valid", "Exact optimum"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    labels = [str(int(seed)) for seed in qaoa["seed"]] + ["Uniform-valid"]
    feasible_values = list(qaoa["feasible_fraction_valid"].astype(float)) + [
        float(uniform["feasible_fraction_valid"])
    ]
    axes[0].bar(labels, feasible_values, color=["#5b8ff9"] * 3 + ["#61dDAA"])
    axes[0].set_ylabel("Probability within valid subspace")
    axes[0].set_title("Joint feasibility")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].grid(axis="y", alpha=0.2)
    x_pos = np.arange(len(labels))
    width = 0.34
    near_values = list(qaoa["near_optimal_fraction_valid"].astype(float)) + [
        float(uniform["near_optimal_fraction_valid"])
    ]
    exact_values = list(qaoa["exact_optimum_fraction_valid"].astype(float)) + [
        float(uniform["exact_optimum_fraction_valid"])
    ]
    axes[1].bar(x_pos - width / 2, near_values, width, label="Near-optimal")
    axes[1].bar(x_pos + width / 2, exact_values, width, label="Exact optimum")
    axes[1].set_xticks(x_pos, labels, rotation=25)
    axes[1].set_ylabel("Probability within valid subspace")
    axes[1].set_title("High-quality route mass")
    axes[1].legend()
    axes[1].grid(axis="y", alpha=0.2)
    fig.suptitle("D=4 constrained QAOA versus uniform-valid sampling")
    _save_figure(figure_dir / "03_d4_quality_probabilities.png")

    resources = pd.read_csv(
        artifacts / "tables" / "circuit_resource_comparison.csv"
    )
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.2))
    for axis, metric, title in zip(
        axes,
        ("depth", "gate_count", "two_qubit_gate_count"),
        ("Depth", "Total gates", "Two-qubit gates"),
        strict=True,
    ):
        axis.bar(["X mixer", "XY constrained"], resources[metric], color=["#65789b", "#f6bd16"])
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=20)
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle("D=4 p=1 circuit-resource overhead")
    _save_figure(figure_dir / "04_d4_resource_overhead.png")

    plt.figure(figsize=(8, 5))
    for seed in (6601, 6602, 6603):
        trace = pd.DataFrame(
            json.loads(
                (
                    artifacts
                    / "d4"
                    / "runs"
                    / f"seed-{seed}"
                    / "optimizer.json"
                ).read_text(encoding="utf-8")
            )
        )
        plt.plot(trace["iteration"], trace["cost"], marker="o", label=str(seed))
    plt.xlabel("Optimizer iteration")
    plt.ylabel("Sampled transformed cost")
    plt.title("D=4 constrained-QAOA optimizer traces")
    plt.legend(title="Seed")
    plt.grid(alpha=0.25)
    _save_figure(figure_dir / "05_d4_optimizer_traces.png")

    figure_paths = sorted(figure_dir.glob("*.png"))
    figure_manifest = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_tables": {
            "d4_results_sha256": sha256_file(
                artifacts / "tables" / "stage6b_d4_results.csv"
            ),
            "d4_seed_summary_sha256": sha256_file(
                artifacts / "tables" / "stage6b_d4_seed_summary.csv"
            ),
            "resource_comparison_sha256": sha256_file(
                artifacts / "tables" / "circuit_resource_comparison.csv"
            ),
        },
        "figures": [
            {"path": str(path.resolve()), "sha256": sha256_file(path)}
            for path in figure_paths
        ],
    }
    figure_manifest_path.write_text(
        json.dumps(figure_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(statistics_path.resolve())
    print(d6_gate_path.resolve())
    print(figure_manifest_path.resolve())


if __name__ == "__main__":
    main()
