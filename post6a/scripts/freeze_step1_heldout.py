"""Freeze the held-out scenario and route manifests before comparison."""

from __future__ import annotations

import json

from holy_qow_post6a.common import artifact_root, sha256_file, write_csv, write_json
from holy_qow_post6a.heldout import build_evaluator, heldout_scenarios, route_manifest


def main() -> None:
    output = artifact_root() / "heldout"
    scenario_path = output / "heldout_scenario_manifest.json"
    route_path = output / "heldout_route_manifest.json"
    csv_path = output / "heldout_scenarios.csv"
    if scenario_path.exists() or route_path.exists() or csv_path.exists():
        raise FileExistsError("held-out manifests are already frozen; refusing overwrite")
    specs = heldout_scenarios()
    if not 10 <= len(specs) <= 30:
        raise ValueError("held-out scenario count must be in the predeclared 10-30 range")
    rows = []
    scenario_records = []
    for spec in specs:
        evaluator = build_evaluator(spec)
        feasible_count = len(evaluator.joint_feasible_assignments())
        if feasible_count <= 0:
            raise ValueError(f"held-out scenario {spec.scenario_id} has no feasible route")
        record = {**spec.to_dict(), "feasible_assignment_count": feasible_count}
        scenario_records.append(record)
        rows.append(
            {
                "scenario_id": spec.scenario_id,
                "category": spec.category,
                "description": spec.description,
                "demand_multipliers": json.dumps(spec.demand_multipliers),
                "capacity_multipliers": json.dumps(record["capacity_multipliers"], sort_keys=True),
                "latency_multipliers": json.dumps(record["latency_multipliers"], sort_keys=True),
                "feasible_assignment_count": feasible_count,
            }
        )
    write_json(
        scenario_path,
        {
            "schema_version": "post6a-steps0-2-v1",
            "status": "FROZEN_BEFORE_ROUTE_COMPARISON",
            "training_scenarios_excluded": ["nominal", "surge", "degradation"],
            "full_link_removal_used": False,
            "scenario_count": len(scenario_records),
            "scenarios": scenario_records,
        },
    )
    write_json(route_path, route_manifest())
    write_csv(csv_path, rows)
    freeze = {
        "scenario_manifest_sha256": sha256_file(scenario_path),
        "route_manifest_sha256": sha256_file(route_path),
        "scenario_table_sha256": sha256_file(csv_path),
    }
    write_json(output / "freeze_record.json", freeze)
    print(scenario_path.resolve())
    print(route_path.resolve())
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
