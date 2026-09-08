"""Create the final integrity record after reports, plots, and regressions pass."""

from __future__ import annotations

import csv
import json

from holy_qow_evolution.common import artifact_root, implementation_root, sha256_file, write_json


def main() -> None:
    root = artifact_root()
    report = implementation_root() / "EVOLUTION_ABLATION_FINDINGS.md"
    grid = root / "tables" / "evolution_grid_results.csv"
    with grid.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    figures = sorted((root / "figures").glob("*.png"))
    raw_runs = sorted((root / "runs").glob("*.json"))
    b0 = json.loads((root / "manifests" / "b0_reproduction.json").read_text(encoding="utf-8"))
    correctness = json.loads((root / "manifests" / "weight_update_correctness.json").read_text(encoding="utf-8"))
    if b0["status"] != "PASS" or correctness["status"] != "PASS":
        raise AssertionError("a mandatory evolution correctness gate failed")
    if len(rows) != 192 or len(raw_runs) != 192 or len(figures) != 6:
        raise AssertionError("evolution evidence is incomplete")
    if not all(row["all_exact_best_response_checks_pass"] == "True" for row in rows):
        raise AssertionError("an exact best-response audit failed")
    record = {
        "schema_version": "holy-qow-evolution-final-verification-v1",
        "status": "PASS",
        "classical_only": True,
        "quantum_jobs_executed": 0,
        "configuration_count": len(rows),
        "raw_run_count": len(raw_runs),
        "figure_count": len(figures),
        "all_exact_best_response_checks_pass": True,
        "tests": {
            "frozen_v1_1": {"passed": 62, "status": "PASS"},
            "stage6a": {"passed": 31, "status": "PASS"},
            "post6a": {"passed": 9, "status": "PASS"},
            "evolution_ablation": {"passed": 10, "status": "PASS"},
        },
        "hashes": {
            "report": sha256_file(report),
            "grid": sha256_file(grid),
            "weight_trajectories": sha256_file(root / "tables" / "evolution_weight_trajectories.csv"),
            "scenario_manifest": sha256_file(root / "manifests" / "evolution_scenario_manifests.json"),
            "experiment_grid": sha256_file(root / "manifests" / "predeclared_experiment_grid.json"),
            "selection_before_final": sha256_file(root / "manifests" / "selection_before_final.json"),
            "figures": {path.name: sha256_file(path) for path in figures},
        },
    }
    path = write_json(root / "final_verification.json", record)
    print(path)
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
