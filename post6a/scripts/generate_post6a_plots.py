"""Generate post-6A Steps 0-2 figures from saved evidence tables only."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from holy_qow_post6a.common import artifact_root

COLORS = {
    "qaoa": "#6F4E9C",
    "random": "#8C96A3",
    "nominal": "#D08770",
    "static": "#5E81AC",
    "adaptive": "#A3BE8C",
}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 180,
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "legend.frameon": False,
        }
    )


def _save(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def raw_vs_conditional(root: Path, figures: Path) -> None:
    data = pd.read_csv(root / "conditional" / "conditional_metrics.csv")
    x = np.arange(len(data))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1))
    raw = ["p_one_hot", "p_joint_feasible", "p_near_optimal"]
    labels = ["One-hot", "Jointly feasible", "Near-optimal"]
    for offset, (column, label) in zip((-0.24, 0.0, 0.24), zip(raw, labels), strict=True):
        axes[0].bar(x + offset, data[column], width=0.22, label=label)
    axes[0].set_yscale("log")
    axes[0].set_xticks(x, [f"D={d}" for d in data["D"]])
    axes[0].set_ylabel("Probability per raw shot (log scale)")
    axes[0].set_title("Raw probability collapses with problem size")
    axes[0].legend()

    width = 0.34
    axes[1].bar(
        x - width / 2,
        data["p_feasible_given_onehot"],
        width,
        label="P(feasible | one-hot)",
        color="#5E81AC",
    )
    axes[1].bar(
        x + width / 2,
        data["p_near_optimal_given_onehot"],
        width,
        label="P(near-optimal | one-hot)",
        color="#A3BE8C",
    )
    axes[1].set_xticks(x, [f"D={d}" for d in data["D"]])
    axes[1].set_ylim(0, 0.55)
    axes[1].set_ylabel("Conditional probability")
    axes[1].set_title("Conditional distribution remains measurable")
    axes[1].legend()
    fig.suptitle("Step 0 — Separate subspace access from in-subspace quality", y=1.02)
    _save(fig, figures / "01_raw_vs_conditional_probability.png")


def matched_valid_quality(root: Path, figures: Path) -> None:
    summary = pd.read_csv(root / "conditional" / "matched_valid_summary.csv")
    x = np.arange(len(summary))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1))
    axes[0].errorbar(
        x,
        summary["random_best_objective_gap_median"],
        yerr=np.vstack(
            [
                summary["random_best_objective_gap_median"]
                - summary["random_best_objective_gap_q25"],
                summary["random_best_objective_gap_q75"]
                - summary["random_best_objective_gap_median"],
            ]
        ),
        fmt="o",
        capsize=4,
        label="Matched random-valid median ± IQR",
        color=COLORS["random"],
    )
    axes[0].scatter(
        x,
        summary["qaoa_best_objective_gap"],
        marker="D",
        s=55,
        label="QAOA",
        color=COLORS["qaoa"],
        zorder=3,
    )
    axes[0].set_xticks(x, [f"D={d}\nN={n}" for d, n in zip(summary["D"], summary["matched_batch_size"], strict=True)])
    axes[0].set_ylabel("Best feasible objective gap (lower is better)")
    axes[0].set_title("Best solution in the same valid-sample budget")
    axes[0].legend()

    axes[1].errorbar(
        x,
        summary["random_near_optimal_fraction_median"],
        yerr=np.vstack(
            [
                summary["random_near_optimal_fraction_median"]
                - summary["random_near_optimal_fraction_q25"],
                summary["random_near_optimal_fraction_q75"]
                - summary["random_near_optimal_fraction_median"],
            ]
        ),
        fmt="o",
        capsize=4,
        label="Matched random-valid median ± IQR",
        color=COLORS["random"],
    )
    axes[1].scatter(
        x,
        summary["qaoa_near_optimal_fraction_given_onehot"],
        marker="D",
        s=55,
        label="QAOA",
        color=COLORS["qaoa"],
        zorder=3,
    )
    axes[1].set_xticks(x, [f"D={d}\nN={n}" for d, n in zip(summary["D"], summary["matched_batch_size"], strict=True)])
    axes[1].set_ylabel("Near-optimal fraction within valid samples")
    axes[1].set_title("Near-optimal concentration")
    axes[1].legend()
    fig.suptitle("Step 0 — QAOA versus matched-size random-valid batches", y=1.02)
    _save(fig, figures / "02_matched_valid_quality.png")


def heldout_regret(root: Path, figures: Path) -> None:
    results = pd.read_csv(root / "heldout" / "heldout_route_results.csv")
    groups = [
        ("nominal_only", "Nominal\nrepresentative", COLORS["nominal"]),
        ("static_uniform_multiscenario", "Static\nuniform", COLORS["static"]),
        ("exact_adaptive", "Adaptive/QAOA/\nminimax same route", COLORS["adaptive"]),
    ]
    values = [results.loc[results.route_id == key, "regret"].values for key, _, _ in groups]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    boxes = ax.boxplot(values, patch_artist=True, widths=0.55, showmeans=True)
    for box, (_, _, color) in zip(boxes["boxes"], groups, strict=True):
        box.set_facecolor(color)
        box.set_alpha(0.8)
    ax.set_xticks(range(1, len(groups) + 1), [label for _, label, _ in groups])
    ax.set_ylabel("Held-out regret")
    ax.set_title("Step 1 — Held-out regret across 24 frozen perturbations")
    ax.text(
        0.02,
        0.97,
        "Exact-adaptive, QAOA-adaptive, and minimax selected (0,1,1,2)",
        transform=ax.transAxes,
        va="top",
        fontsize=8,
    )
    _save(fig, figures / "03_heldout_regret_distribution.png")


def heldout_survival(root: Path, figures: Path) -> None:
    summary = pd.read_csv(root / "heldout" / "heldout_route_summary.csv")
    labels = ["Nominal", "Static", "Exact\nadaptive", "QAOA\nadaptive", "Minimax"]
    colors = [COLORS["nominal"], COLORS["static"], COLORS["adaptive"], COLORS["qaoa"], "#B48EAD"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(labels, 100 * summary["survival_rate"], color=colors)
    ax.set_ylim(0, 106)
    ax.set_ylabel("Feasible held-out scenarios (%)")
    ax.set_title("Step 1 — Survival under frozen unseen pressures")
    feasible_counts = summary["scenario_count"] - summary["violating_scenarios"]
    for bar, count in zip(bars, feasible_counts, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{int(count)}/24", ha="center", fontsize=8)
    _save(fig, figures / "04_heldout_survival.png")


def seed_repeatability(root: Path, figures: Path) -> None:
    data = pd.read_csv(root / "repeatability" / "d6_repeatability.csv")
    qaoa = data[data.method == "qaoa"].sort_values("optimizer_seed")
    random_bits = data[data.method == "uniform_random_bitstrings"].sort_values("optimizer_seed")
    x = np.arange(len(qaoa))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, column, title in (
        (axes[0], "p_one_hot", "One-hot probability"),
        (axes[1], "p_joint_feasible", "Jointly feasible probability"),
    ):
        ax.plot(x, qaoa[column], "o-", label="QAOA", color=COLORS["qaoa"])
        ax.plot(x, random_bits[column], "s--", label="Random bitstrings", color=COLORS["random"])
        ax.set_yscale("log")
        ax.set_xticks(x, qaoa["optimizer_seed"].astype(str))
        ax.set_xlabel("Optimizer seed")
        ax.set_ylabel("Probability (log scale)")
        ax.set_title(title)
        ax.legend()
    fig.suptitle("Step 2 — D=6 raw-probability repeatability", y=1.02)
    _save(fig, figures / "05_d6_seed_repeatability.png")


def conditional_by_seed(root: Path, figures: Path) -> None:
    data = pd.read_csv(root / "repeatability" / "d6_repeatability.csv")
    qaoa = data[data.method == "qaoa"].sort_values("optimizer_seed")
    valid = data[data.method == "uniform_random_valid_routes"].sort_values("optimizer_seed")
    matched = pd.read_csv(root / "repeatability" / "d6_matched_valid_summary.csv").sort_values("optimizer_seed")
    x = np.arange(len(qaoa))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    width = 0.36
    axes[0].bar(x - width / 2, qaoa["p_feasible_given_onehot"], width, label="QAOA", color=COLORS["qaoa"])
    axes[0].bar(x + width / 2, valid["p_feasible_given_onehot"], width, label="Random valid (4096)", color=COLORS["random"])
    axes[0].set_xticks(x, qaoa["optimizer_seed"].astype(str))
    axes[0].set_xlabel("Optimizer seed")
    axes[0].set_ylabel("P(feasible | one-hot)")
    axes[0].set_title("Conditional feasibility")
    axes[0].legend()

    axes[1].errorbar(
        x,
        matched["random_best_objective_gap_median"],
        yerr=np.vstack(
            [
                matched["random_best_objective_gap_median"] - matched["random_best_objective_gap_q25"],
                matched["random_best_objective_gap_q75"] - matched["random_best_objective_gap_median"],
            ]
        ),
        fmt="o",
        capsize=4,
        label="Matched random-valid median ± IQR",
        color=COLORS["random"],
    )
    axes[1].scatter(x, qaoa["best_feasible_objective_gap"], marker="D", s=50, label="QAOA", color=COLORS["qaoa"], zorder=3)
    axes[1].set_xticks(x, [f"{seed}\nN={count}" for seed, count in zip(qaoa["optimizer_seed"], qaoa["one_hot_count"], strict=True)])
    axes[1].set_xlabel("Optimizer seed and matched valid sample count")
    axes[1].set_ylabel("Best feasible objective gap")
    axes[1].set_title("Conditional solution quality")
    axes[1].legend()
    fig.suptitle("Step 2 — In-subspace quality varies and is not significant", y=1.02)
    _save(fig, figures / "06_d6_conditional_quality_by_seed.png")


def main() -> None:
    _style()
    root = artifact_root()
    figures = root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    raw_vs_conditional(root, figures)
    matched_valid_quality(root, figures)
    heldout_regret(root, figures)
    heldout_survival(root, figures)
    seed_repeatability(root, figures)
    conditional_by_seed(root, figures)
    for path in sorted(figures.glob("*.png")):
        print(path.resolve())


if __name__ == "__main__":
    main()
