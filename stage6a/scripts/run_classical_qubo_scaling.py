"""Generate classical and QUBO scaling records without Classiq access."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from time import perf_counter

from qera_scaling.benchmarks import classical_record
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import core_instances
from qera_scaling.qubo import build_energy_spec, qubo_metrics


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    scaling = root / "artifacts" / "scaling"
    classical_dir = scaling / "classical"
    qubo_dir = scaling / "qubo"
    table_dir = scaling / "tables"
    for directory in (classical_dir, qubo_dir, table_dir):
        directory.mkdir(parents=True, exist_ok=True)
    classical_rows = []
    qubo_rows = []
    for instance in core_instances():
        evaluator = ScalingEvaluator(instance)
        classical = classical_record(evaluator)
        (classical_dir / f"{instance.instance_id}.json").write_text(
            json.dumps(classical, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        classical_rows.append(
            {
                key: classical[key]
                for key in (
                    "instance_id",
                    "seed",
                    "nodes",
                    "edges",
                    "D",
                    "K",
                    "S",
                    "logical_bits",
                    "valid_assignments",
                    "exact_status",
                    "exact_runtime_seconds",
                    "exact_weighted_cost",
                    "exact_worst_case_regret",
                    "minimax_runtime_seconds",
                    "joint_feasible_count",
                    "joint_feasible_fraction_valid",
                    "greedy_runtime_seconds",
                    "local_search_runtime_seconds",
                    "simulated_annealing_runtime_seconds",
                    "random_valid_feasible_fraction",
                )
            } | {
                "greedy_weighted_cost": classical["greedy"]["weighted_cost"],
                "greedy_worst_case_regret": classical["greedy"]["worst_case_regret"],
                "local_search_weighted_cost": classical["local_search"]["weighted_cost"],
                "local_search_worst_case_regret": classical["local_search"]["worst_case_regret"],
                "simulated_annealing_weighted_cost": classical["simulated_annealing"]["weighted_cost"],
                "simulated_annealing_worst_case_regret": classical["simulated_annealing"]["worst_case_regret"],
                "random_valid_best_weighted_cost": classical["random_valid_best"]["weighted_cost"],
                "random_valid_best_worst_case_regret": classical["random_valid_best"]["worst_case_regret"],
            }
        )
        start = perf_counter()
        spec = build_energy_spec(
            evaluator, (1.0 / 3.0,) * 3, objective_mode="cost"
        )
        metrics = {
            "instance_id": instance.instance_id,
            "D": instance.demand_count,
            "K": instance.paths_per_demand,
            "S": instance.scenario_count,
            "construction_runtime_seconds": perf_counter() - start,
            **qubo_metrics(spec),
        }
        (qubo_dir / f"{instance.instance_id}.json").write_text(
            json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        qubo_rows.append(metrics)
        print(f"D={instance.demand_count} classical+QUBO complete")
    _write_csv(table_dir / "scaling_classical.csv", classical_rows)
    _write_csv(table_dir / "scaling_qubo.csv", qubo_rows)
    print(table_dir.resolve())


if __name__ == "__main__":
    main()
