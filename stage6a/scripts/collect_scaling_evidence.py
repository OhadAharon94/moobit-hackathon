"""Collect Stage 6A QAOA and provenance tables from saved evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import core_instances
from qera_scaling.postprocess import process_sample_frame
from qera_scaling.provenance import sha256_file
from qera_scaling.qubo import build_energy_spec

WEIGHTS = (1.0 / 3.0,) * 3
METHODS = ("qaoa", "uniform_random_bitstrings", "uniform_random_valid_routes")


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _row(instance, method: str, summary: dict, manifest: dict | None) -> dict:
    return {
        "instance_id": instance.instance_id,
        "D": instance.demand_count,
        "method": method,
        "status": summary["status"],
        "total_shots": summary["total_shots"],
        "observed_state_count": summary["observed_state_count"],
        "one_hot_probability": summary["one_hot_probability"],
        "theoretical_uniform_one_hot_probability": summary[
            "theoretical_uniform_one_hot_probability"
        ],
        "joint_feasible_probability": summary["joint_feasible_probability"],
        "exact_joint_optimum_probability": summary[
            "exact_joint_optimum_probability"
        ],
        "near_optimal_joint_probability_gap_0_01": summary[
            "near_optimal_joint_probability_gap_0_01"
        ],
        "exact_joint_objective": summary["exact_joint_objective"],
        "selected_assignment": json.dumps(summary["selected_assignment"]),
        "selected_objective": summary["selected_objective"],
        "selected_exact_gap": summary["selected_exact_gap"],
        "selected_relative_gap": summary["selected_relative_gap"],
        "exact_minimax_regret": summary["exact_minimax_regret"],
        "best_sampled_worst_case_regret": summary[
            "best_sampled_worst_case_regret"
        ],
        "best_sampled_regret_gap": summary["best_sampled_regret_gap"],
        "optimizer_trace_length": (
            manifest.get("optimizer_trace_length") if method == "qaoa" and manifest else None
        ),
        "optimizer_shots": (
            manifest.get("optimizer_shots") if method == "qaoa" and manifest else None
        ),
        "runtime_seconds": (
            manifest.get("execution_runtime_seconds")
            if method == "qaoa" and manifest
            else None
        ),
        "seed": (
            manifest.get("seed") if method == "qaoa" and manifest else instance.seed
        ),
        "data_source": "frozen-v1.1" if instance.demand_count == 4 else "stage6a",
    }


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def main() -> None:
    stage6a_root = Path(__file__).resolve().parents[1]
    implementation_root = stage6a_root.parent
    scaling_root = stage6a_root / "artifacts" / "scaling"
    table_dir = scaling_root / "tables"
    qaoa_rows = []
    manifest_rows = []
    for instance in core_instances():
        evaluator = ScalingEvaluator(instance)
        spec = build_energy_spec(evaluator, WEIGHTS, "cost")
        summaries: dict[str, dict] = {}
        run_manifest = None
        if instance.demand_count == 4:
            run_dir = implementation_root / "artifacts" / "runs" / "uniform_cost_p1_smoke"
            run_manifest = json.loads(
                (run_dir / "manifest.json").read_text(encoding="utf-8")
            )
            frames = {
                "qaoa": pd.read_csv(run_dir / "samples_raw.csv"),
                "uniform_random_bitstrings": pd.read_csv(
                    implementation_root / "artifacts" / "tables" / "uniform_random_bitstrings.csv"
                ),
                "uniform_random_valid_routes": pd.read_csv(
                    implementation_root / "artifacts" / "tables" / "uniform_random_valid_routes.csv"
                ),
            }
            for method, frame in frames.items():
                _, summaries[method] = process_sample_frame(
                    frame, evaluator, spec, WEIGHTS, declared_shots=4096
                )
            qprog_path = implementation_root / "artifacts" / "circuits" / "uniform_cost_p1.qprog"
            synthesis_manifest = implementation_root / "artifacts" / "circuits" / "uniform_cost_p1.synthesis.json"
            qaoa_summary_path = run_dir / "summary.json"
        elif instance.demand_count <= 6:
            run_dir = (
                scaling_root
                / "qaoa"
                / f"{instance.instance_id}-p1-uniform-cost"
            )
            run_manifest = json.loads(
                (run_dir / "manifest.json").read_text(encoding="utf-8")
            )
            summaries["qaoa"] = json.loads(
                (run_dir / "summary.json").read_text(encoding="utf-8")
            )
            for method in METHODS[1:]:
                summaries[method] = json.loads(
                    (run_dir / "controls" / method / "summary.json").read_text(
                        encoding="utf-8"
                    )
                )
            qprog_path = scaling_root / "circuits" / f"{instance.instance_id}-p1.qprog"
            synthesis_manifest = scaling_root / "circuits" / f"{instance.instance_id}-p1.synthesis.json"
            qaoa_summary_path = run_dir / "summary.json"
        else:
            qprog_path = scaling_root / "circuits" / f"{instance.instance_id}-p1.qprog"
            synthesis_manifest = scaling_root / "circuits" / f"{instance.instance_id}-p1.synthesis.json"
            qaoa_summary_path = None

        for method in METHODS:
            if method in summaries:
                qaoa_rows.append(_row(instance, method, summaries[method], run_manifest))

        instance_path = scaling_root / "instances" / f"{instance.instance_id}.json"
        classical_path = scaling_root / "classical" / f"{instance.instance_id}.json"
        qubo_path = scaling_root / "qubo" / f"{instance.instance_id}.json"
        qmod_path = scaling_root / "circuits" / f"{instance.instance_id}-p1.qmod.json"
        manifest_rows.append(
            {
                "instance_id": instance.instance_id,
                "D": instance.demand_count,
                "record_status": (
                    "COMPLETE" if qaoa_summary_path is not None else "SYNTHESIS_ONLY"
                ),
                "instance_path": _relative(instance_path, implementation_root),
                "instance_sha256": sha256_file(instance_path),
                "classical_path": _relative(classical_path, implementation_root),
                "classical_sha256": sha256_file(classical_path),
                "qubo_path": _relative(qubo_path, implementation_root),
                "qubo_sha256": sha256_file(qubo_path),
                "qmod_path": _relative(qmod_path, implementation_root),
                "qmod_sha256": sha256_file(qmod_path),
                "qprog_path": _relative(qprog_path, implementation_root),
                "qprog_sha256": sha256_file(qprog_path),
                "synthesis_manifest_path": _relative(
                    synthesis_manifest, implementation_root
                ),
                "synthesis_manifest_sha256": sha256_file(synthesis_manifest),
                "qaoa_summary_path": (
                    _relative(qaoa_summary_path, implementation_root)
                    if qaoa_summary_path is not None
                    else ""
                ),
                "qaoa_summary_sha256": (
                    sha256_file(qaoa_summary_path)
                    if qaoa_summary_path is not None
                    else ""
                ),
                "warning": (
                    "D=8 is synthesis-only; no statevector QAOA execution was attempted."
                    if instance.demand_count == 8
                    else ""
                ),
            }
        )
    _write_csv(table_dir / "scaling_qaoa.csv", qaoa_rows)
    _write_csv(table_dir / "scaling_manifest.csv", manifest_rows)
    print((table_dir / "scaling_qaoa.csv").resolve())
    print((table_dir / "scaling_manifest.csv").resolve())


if __name__ == "__main__":
    main()
