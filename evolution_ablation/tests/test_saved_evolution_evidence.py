from __future__ import annotations

import csv
import json

from holy_qow_evolution.common import artifact_root, sha256_file


def test_b0_and_evidence_gates_pass() -> None:
    root = artifact_root()
    b0 = json.loads((root / "manifests" / "b0_reproduction.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "manifests" / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert b0["status"] == "PASS"
    assert all(b0["checks"].values())
    assert evidence["status"] == "COMPLETE"
    assert evidence["solver"] == "exact exhaustive classical only; no quantum execution"
    assert evidence["raw_run_count"] == 192
    assert evidence["final_test_used_for_selection"] is False


def test_saved_grid_is_complete_and_exact() -> None:
    root = artifact_root()
    with (root / "tables" / "evolution_grid_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 192
    assert all(row["all_exact_best_response_checks_pass"] == "True" for row in rows)
    assert len({row["run_id"] for row in rows}) == 192
    assert all((root / "runs" / f"{row['run_id']}.json").is_file() for row in rows)


def test_selection_was_hash_bound_before_final_evaluation() -> None:
    root = artifact_root()
    selection = json.loads((root / "manifests" / "selection_before_final.json").read_text(encoding="utf-8"))
    validation_path = root / "tables" / "evolution_validation_results.csv"
    assert selection["validation_summary_sha256"] == sha256_file(validation_path)
    assert selection["final_test_consulted_for_selection"] is False
    supplement = json.loads((root / "manifests" / "adaptive_eligibility_supplement.json").read_text(encoding="utf-8"))
    assert supplement["final_test_columns_used"] is False
    assert supplement["selected_genuinely_adaptive_run_id"] == "B6-eta-edge-s8-eta0p1-t2-rho0"
