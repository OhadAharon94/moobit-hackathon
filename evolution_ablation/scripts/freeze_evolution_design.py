"""Freeze scenario pools and the entire ablation grid before final-test analysis."""

from __future__ import annotations

import json

from holy_qow_evolution.common import artifact_root, implementation_root, sha256_file, sha256_payload, write_json
from holy_qow_evolution.engine import ScenarioOracle
from holy_qow_evolution.scenarios import final_test_pool, training_pool, validation_pool


def config(run_family: str, s: int, eta: float, iterations: int, rho: float) -> dict:
    return {
        "run_id": f"{run_family}-s{s}-eta{eta:g}-t{iterations}-rho{rho:g}".replace(".", "p"),
        "run_family": run_family,
        "S": s,
        "eta": eta,
        "T": iterations,
        "rho": rho,
        "objective": "weighted normalized cost",
        "weight_signal": "per-scenario normalized regret clipped to [0,1]",
        "inner_solver": "exact exhaustive best response over the jointly training-feasible domain",
    }


def predeclared_grid() -> list[dict]:
    rows: list[dict] = []
    for s in (3, 5, 8, 12):
        for eta in (0.0, 0.25, 0.5, 1.0):
            for iterations in (3, 5):
                rows.append(config("B4-focused", s, eta, iterations, 0.0))
    for s in (3, 5, 8, 12):
        for eta in (0.25, 0.5, 1.0):
            for iterations in (3, 5):
                for rho in (0.1, 0.25, 0.5):
                    rows.append(config("B5-diversity", s, eta, iterations, rho))
    for s in (3, 5, 8, 12):
        for eta in (0.1, 2.0):
            for iterations in (1, 2, 3, 5, 10):
                rows.append(config("B6-eta-edge", s, eta, iterations, 0.0))
    for s in (3, 5, 8, 12):
        for eta in (0.0, 0.25, 0.5, 1.0):
            for iterations in (1, 2, 10):
                rows.append(config("B6-time-edge", s, eta, iterations, 0.0))
    ids = [row["run_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise AssertionError("predeclared grid contains duplicate configurations")
    return rows


def main() -> None:
    out = artifact_root() / "manifests"
    scenario_path = out / "evolution_scenario_manifests.json"
    design_path = out / "predeclared_experiment_grid.json"
    if scenario_path.exists() or design_path.exists():
        raise FileExistsError("evolution study design is already frozen; refusing overwrite")
    training = training_pool()
    validation = validation_pool()
    final = final_test_pool()
    pools = {"training": training, "validation": validation, "final_test": final}
    for pool_name, scenarios in pools.items():
        ids = [item.scenario_id for item in scenarios]
        fingerprints = [item.fingerprint() for item in scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{pool_name} contains duplicate scenario IDs")
        if len(fingerprints) != len(set(fingerprints)):
            raise ValueError(f"{pool_name} contains duplicate scenario parameterizations")
        if any(item.to_dict()["feasible_assignment_count"] <= 0 for item in scenarios):
            raise ValueError(f"{pool_name} contains a scenario with no feasible route")
        if any(value <= 0.0 for item in scenarios for value in item.capacity_multipliers.values()):
            raise ValueError(f"{pool_name} uses a full link removal")
    id_sets = {name: {item.scenario_id for item in items} for name, items in pools.items()}
    fingerprint_sets = {name: {item.fingerprint() for item in items} for name, items in pools.items()}
    names = tuple(pools)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            if id_sets[left] & id_sets[right]:
                raise ValueError(f"scenario ID leakage between {left} and {right}")
            if fingerprint_sets[left] & fingerprint_sets[right]:
                raise ValueError(f"scenario parameter leakage between {left} and {right}")
    nested_counts = {
        str(s): len(ScenarioOracle(training[:s]).joint_feasible_assignments())
        for s in (3, 5, 8, 12)
    }
    if any(count <= 0 for count in nested_counts.values()):
        raise ValueError("a nested training pool has no jointly feasible best-response domain")
    final_manifest = (
        implementation_root()
        / "artifacts"
        / "post6a"
        / "heldout"
        / "heldout_scenario_manifest.json"
    )
    scenario_manifest = {
        "schema_version": "holy-qow-evolution-scenarios-v1",
        "status": "FROZEN_BEFORE_ABLATION_AND_FINAL_TEST_INSPECTION",
        "training_pool_is_nested": True,
        "training_prefix_sizes": [3, 5, 8, 12],
        "original_s3_is_first_prefix": True,
        "full_link_removal_used": False,
        "training_joint_feasible_counts": nested_counts,
        "pools": {
            name: [item.to_dict() for item in scenarios]
            for name, scenarios in pools.items()
        },
        "pool_payload_hashes": {
            name: sha256_payload([item.parameter_payload() for item in scenarios])
            for name, scenarios in pools.items()
        },
        "frozen_final_source": {
            "path": str(final_manifest.resolve()),
            "sha256": sha256_file(final_manifest),
        },
        "leakage_check": "PASS: pairwise-disjoint IDs and parameter fingerprints",
    }
    write_json(scenario_path, scenario_manifest)
    grid = predeclared_grid()
    design = {
        "schema_version": "holy-qow-evolution-grid-v1",
        "status": "PREDECLARED_BEFORE_FINAL_TEST_ANALYSIS",
        "config_count": len(grid),
        "focused_count": sum(row["run_family"] == "B4-focused" for row in grid),
        "diversity_count": sum(row["run_family"] == "B5-diversity" for row in grid),
        "edge_count": sum(row["run_family"].startswith("B6") for row in grid),
        "scenario_manifest_sha256": sha256_file(scenario_path),
        "validation_selection_rule": [
            "maximize validation survival rate",
            "minimize validation maximum overflow",
            "minimize validation worst-case regret",
            "minimize validation mean regret",
            "minimize frozen nominal cost",
            "lexicographic configuration parameters for deterministic ties",
        ],
        "selection_groups": {
            "adaptive": "eta > 0",
            "static_uniform": "eta = 0",
        },
        "final_test_policy": "selection is frozen from training/validation evidence before final metrics are computed; final outcomes never alter selection",
        "configurations": grid,
    }
    write_json(design_path, design)
    freeze_record = {
        "scenario_manifest_sha256": sha256_file(scenario_path),
        "experiment_grid_sha256": sha256_file(design_path),
        "config_count": len(grid),
    }
    write_json(out / "freeze_record.json", freeze_record)
    print(scenario_path.resolve())
    print(design_path.resolve())
    print(json.dumps(freeze_record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
