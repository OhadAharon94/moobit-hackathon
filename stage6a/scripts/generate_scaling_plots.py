"""Generate the five Stage 6A figures from saved CSV records only."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

_PLOT_CACHE = Path(tempfile.gettempdir()) / "qera-stage6a-matplotlib"
_PLOT_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_PLOT_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _finish(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    stage6a_root = Path(__file__).resolve().parents[1]
    scaling_root = stage6a_root / "artifacts" / "scaling"
    tables = scaling_root / "tables"
    figures = scaling_root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    synthesis = pd.read_csv(tables / "scaling_synthesis.csv")
    qubo = pd.read_csv(tables / "scaling_qubo.csv")
    qaoa = pd.read_csv(tables / "scaling_qaoa.csv")
    colors = {
        "qaoa": "#4C78A8",
        "uniform_random_bitstrings": "#F58518",
        "uniform_random_valid_routes": "#54A24B",
    }
    labels = {
        "qaoa": "QAOA p=1",
        "uniform_random_bitstrings": "Random bitstrings",
        "uniform_random_valid_routes": "Random valid routes",
    }

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(synthesis["D"], synthesis["logical_bits"], "o-", label="Logical route bits")
    ax.plot(
        synthesis["D"],
        synthesis["synthesized_qubits"],
        "s--",
        label="Synthesized qubits",
    )
    ax.set(xlabel="Number of demands D", ylabel="Qubits", title="Q-ERA width scaling (K=3)")
    ax.set_xticks(synthesis["D"])
    ax.grid(alpha=0.25)
    ax.legend()
    _finish(fig, figures / "01_quantum_width.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].plot(synthesis["D"], synthesis["depth"], "o-", color="#4C78A8")
    axes[0].set(xlabel="D", ylabel="Circuit depth", title="Depth")
    axes[1].plot(
        synthesis["D"], synthesis["two_qubit_gate_count"], "o-", color="#E45756"
    )
    axes[1].set(xlabel="D", ylabel="Two-qubit gates", title="Entangling-gate count")
    for ax in axes:
        ax.set_xticks(synthesis["D"])
        ax.grid(alpha=0.25)
    fig.suptitle("Classiq p=1 resource scaling")
    _finish(fig, figures / "02_circuit_resources.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].plot(qubo["D"], qubo["nonzero_quadratic"], "o-", color="#B279A2")
    axes[0].set(xlabel="D", ylabel="Nonzero couplings", title="QUBO interactions")
    axes[1].plot(qubo["D"], qubo["quadratic_density"], "o-", color="#72B7B2")
    axes[1].set(xlabel="D", ylabel="Fraction of possible pairs", title="Coupling density")
    axes[1].set_ylim(0, 1)
    for ax in axes:
        ax.set_xticks(qubo["D"])
        ax.grid(alpha=0.25)
    fig.suptitle("QUBO interaction scaling")
    _finish(fig, figures / "03_qubo_interactions.png")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharex=True)
    for method, group in qaoa.groupby("method"):
        group = group.sort_values("D")
        axes[0].plot(
            group["D"], group["one_hot_probability"], "o-", color=colors[method], label=labels[method]
        )
        axes[1].plot(
            group["D"], group["joint_feasible_probability"], "o-", color=colors[method], label=labels[method]
        )
    axes[0].set(xlabel="D", ylabel="Probability mass", title="One-hot valid")
    axes[1].set(xlabel="D", ylabel="Probability mass", title="Jointly capacity-feasible")
    for ax in axes:
        ax.set_yscale("log")
        ax.set_xticks(sorted(qaoa["D"].unique()))
        ax.grid(alpha=0.25, which="both")
    axes[1].legend(loc="best")
    fig.suptitle("Feasible sampling probability (4,096 shots per method)")
    _finish(fig, figures / "04_feasible_probability.png")

    pivot = qaoa.pivot(index="D", columns="method", values="selected_relative_gap") * 100.0
    ordered = [method for method in METHODS if method in pivot.columns]
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    pivot[ordered].plot.bar(ax=ax, color=[colors[method] for method in ordered])
    ax.set(
        xlabel="Number of demands D",
        ylabel="Best feasible objective gap (%)",
        title="Solution quality relative to exact enumeration",
    )
    ax.grid(axis="y", alpha=0.25)
    ax.legend([labels[method] for method in ordered])
    _finish(fig, figures / "05_solution_quality.png")
    for path in sorted(figures.glob("*.png")):
        print(path.resolve())


METHODS = ("qaoa", "uniform_random_bitstrings", "uniform_random_valid_routes")


if __name__ == "__main__":
    main()
