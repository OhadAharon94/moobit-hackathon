"""Replay and summarize the three saved adaptive QAOA solves."""

from __future__ import annotations

from pathlib import Path

from qera.adaptive import run_adaptive
from qera.classiq_solver import SavedQuantumInnerSolver
from qera.evaluate import Evaluator
from qera.records import write_json


def main() -> None:
    implementation_root = Path(__file__).resolve().parents[1]
    run_root = implementation_root / "artifacts" / "runs"
    run_names = (
        "uniform_cost_p1_smoke",
        "adaptive_cost_t1",
        "adaptive_cost_t2",
    )
    adaptive = run_adaptive(
        SavedQuantumInnerSolver(run_root, run_names), Evaluator(), "cost"
    )
    output = write_json(
        run_root / "adaptive_cost" / "summary.json",
        {
            "status": adaptive.status,
            "best_assignment": adaptive.best_assignment,
            "steps": adaptive.steps,
            "source_runs": run_names,
        },
    )
    print(output)
    print(f"status={adaptive.status}")
    print(f"best_assignment={adaptive.best_assignment}")
    for step in adaptive.steps:
        print(
            f"t={step.iteration} weights={step.request.scenario_weights} "
            f"assignment={step.result.assignment} worst_regret={step.worst_regret:.9f} "
            f"best_so_far={step.best_so_far}"
        )


if __name__ == "__main__":
    main()
