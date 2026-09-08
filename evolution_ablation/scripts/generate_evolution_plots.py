"""Generate the six predeclared evolution/generalization figures from saved tables."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from holy_qow_evolution.common import artifact_root, sha256_file, write_json


COLORS = {3: "#d1495b", 5: "#edae49", 8: "#00798c", 12: "#30638e"}


def finish(fig: plt.Figure, path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    out = artifact_root()
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(out / "tables" / "evolution_grid_results.csv")
    trajectories = pd.read_csv(out / "tables" / "evolution_weight_trajectories.csv")
    focused = grid[grid["run_family"] == "B4-focused"].copy()

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    for s in (3, 5, 8, 12):
        group = focused[focused["S"] == s].groupby("eta")["final_survival_rate"].mean()
        ax.plot(group.index, group.values, marker="o", label=f"S={s}", color=COLORS[s])
    ax.set(xlabel="Selection strength η", ylabel="Mean final-test survival", ylim=(0.89, 1.01), title="Held-out survival under focused adaptation sweep")
    ax.grid(alpha=0.25)
    ax.legend(ncol=4, fontsize=8)
    finish(fig, figures / "01_survival_vs_eta.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    for s in (3, 5, 8, 12):
        group = focused[focused["S"] == s].groupby("eta")["final_worst_regret"].mean()
        ax.plot(group.index, group.values, marker="o", label=f"S={s}", color=COLORS[s])
    ax.set(xlabel="Selection strength η", ylabel="Mean final-test worst regret", title="Strong selection harms the low-diversity S=3 pool")
    ax.grid(alpha=0.25)
    ax.legend(ncol=4, fontsize=8)
    finish(fig, figures / "02_worst_regret_vs_eta.png")

    adaptive = grid[(grid["eta"] > 0.0) & (grid["T"] > 1)].copy()
    adaptive["collapse_fraction"] = 1.0 - adaptive["final_effective_fraction"]
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for s in (3, 5, 8, 12):
        group = adaptive[adaptive["S"] == s]
        ax.scatter(group["collapse_fraction"], group["final_worst_regret"], s=28, alpha=0.65, label=f"S={s}", color=COLORS[s])
    ax.set(xlabel="Weight concentration 1 − N_eff/S", ylabel="Final-test worst regret", title="Weight concentration correlates with worse robustness")
    ax.grid(alpha=0.25)
    ax.legend()
    finish(fig, figures / "03_effective_environments_vs_generalization.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.5))
    means = focused.groupby("S")["final_survival_rate"].mean().reindex([3, 5, 8, 12])
    ax.bar([str(value) for value in means.index], means.values, color=[COLORS[int(value)] for value in means.index])
    ax.set(xlabel="Training environments S", ylabel="Mean final-test survival", ylim=(0.89, 1.01), title="Additional environment diversity removes the S=3 failure mode")
    ax.grid(axis="y", alpha=0.25)
    finish(fig, figures / "04_training_S_vs_survival.png")

    matched = pd.concat(
        [focused[focused["eta"] > 0.0], grid[grid["run_family"] == "B5-diversity"]],
        ignore_index=True,
    )
    heat = matched.pivot_table(index="eta", columns="rho", values="final_worst_regret", aggfunc="mean").sort_index()
    fig, ax = plt.subplots(figsize=(6.6, 4.5))
    image = ax.imshow(heat.values, cmap="YlOrRd", aspect="auto", vmin=heat.values.min(), vmax=heat.values.max())
    ax.set_xticks(range(len(heat.columns)), [f"{value:g}" for value in heat.columns])
    ax.set_yticks(range(len(heat.index)), [f"{value:g}" for value in heat.index])
    ax.set(xlabel="Diversity mixing ρ", ylabel="Selection strength η", title="Mean final-test worst regret (matched B5 settings)")
    for y in range(len(heat.index)):
        for x in range(len(heat.columns)):
            ax.text(x, y, f"{heat.iloc[y, x]:.3f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, label="Worst regret")
    finish(fig, figures / "05_eta_rho_heatmap.png")

    examples = {
        "ρ=0 (original)": "B4-focused-s3-eta1-t3-rho0",
        "ρ=0.5": "B5-diversity-s3-eta1-t3-rho0p5",
    }
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, (label, run_id) in zip(axes, examples.items(), strict=True):
        rows = trajectories[trajectories["run_id"] == run_id].sort_values("iteration")
        weights = np.array([json.loads(value) for value in rows["weights"]])
        for index, scenario in enumerate(("nominal", "surge", "degradation")):
            ax.plot(rows["iteration"], weights[:, index], marker="o", label=scenario)
        ax.set(xlabel="Outer iteration", title=label, ylim=(0.2, 0.52))
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Scenario weight")
    axes[1].legend(fontsize=8)
    fig.suptitle("Diversity mixing prevents the S=3 best-response switch")
    finish(fig, figures / "06_weight_trajectory_examples.png")

    paths = sorted(figures.glob("*.png"))
    write_json(
        figures / "figure_manifest.json",
        {
            "schema_version": "holy-qow-evolution-figures-v1",
            "source_tables_only": True,
            "figures": {path.name: sha256_file(path) for path in paths},
        },
    )
    print("\n".join(str(path.resolve()) for path in paths))


if __name__ == "__main__":
    main()
