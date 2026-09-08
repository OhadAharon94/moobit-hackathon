"""Reprocess frozen QAOA evidence and record Gate 0A without changing it."""

from __future__ import annotations

import json
import math

import pandas as pd

from holy_qow_post6a.common import artifact_root, sha256_file, write_json
from holy_qow_post6a.conditional import load_reprocessed_qaoa, qaoa_input_paths

CHECKED_SUMMARY_FIELDS = (
    "status",
    "total_shots",
    "one_hot_probability",
    "joint_feasible_probability",
    "near_optimal_joint_probability_gap_0_01",
    "exact_joint_objective",
    "selected_exact_gap",
    "best_sampled_worst_case_regret",
)


def _equal(left, right) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-12)
    return left == right


def main() -> None:
    runs = []
    discrepancies = []
    for D in (4, 5, 6):
        raw_path, summary_path, manifest_path = qaoa_input_paths(D)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        recorded = json.loads(summary_path.read_text(encoding="utf-8"))
        _, reproduced = load_reprocessed_qaoa(D)
        decoded_shots = int(pd.read_csv(raw_path)["counts"].sum())
        field_checks = {}
        for key in CHECKED_SUMMARY_FIELDS:
            if recorded.get(key) is None:
                field_checks[key] = "NOT_RECORDED"
                continue
            field_checks[key] = _equal(recorded.get(key), reproduced.get(key))
            if field_checks[key] is False:
                discrepancies.append(
                    {
                        "D": D,
                        "field": key,
                        "recorded": recorded.get(key),
                        "reproduced": reproduced.get(key),
                    }
                )
        if decoded_shots != int(manifest["final_shots"]):
            discrepancies.append(
                {
                    "D": D,
                    "field": "decoded_shots",
                    "recorded": manifest["final_shots"],
                    "reproduced": decoded_shots,
                }
            )
        runs.append(
            {
                "D": D,
                "raw_path": str(raw_path.resolve()),
                "raw_sha256": sha256_file(raw_path),
                "recorded_summary_path": str(summary_path.resolve()),
                "recorded_summary_sha256": sha256_file(summary_path),
                "manifest_path": str(manifest_path.resolve()),
                "manifest_sha256": sha256_file(manifest_path),
                "recorded_shots": int(manifest["final_shots"]),
                "decoded_shots": decoded_shots,
                "field_checks": field_checks,
            }
        )
    record = {
        "schema_version": "post6a-steps0-2-v1",
        "gate": "0A_artifact_consistency",
        "status": "PASS" if not discrepancies else "FAIL",
        "float_tolerance": {"relative": 1e-10, "absolute": 1e-12},
        "runs": runs,
        "discrepancies": discrepancies,
    }
    output = artifact_root() / "baseline_verification.json"
    write_json(output, record)
    print(output.resolve())
    print(json.dumps(record, indent=2, sort_keys=True))
    if discrepancies:
        raise SystemExit("Gate 0A failed")


if __name__ == "__main__":
    main()
