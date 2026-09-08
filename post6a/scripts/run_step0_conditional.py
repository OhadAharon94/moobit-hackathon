"""Run Step 0 from existing Stage 6A evidence only."""

from __future__ import annotations

import json
from pathlib import Path

from holy_qow_post6a.common import artifact_root, sha256_file, write_csv, write_json
from holy_qow_post6a.conditional import (
    MATCHED_BATCHES,
    NEAR_OPTIMAL_GAP,
    assert_finite_record,
    conditional_record,
    load_reprocessed_qaoa,
    matched_summary,
    matched_valid_batches,
    qaoa_input_paths,
)


def main() -> None:
    output = artifact_root() / "conditional"
    output.mkdir(parents=True, exist_ok=True)
    conditional_rows = []
    matched_rows = []
    matched_summaries = []
    inputs = []
    for D in (4, 5, 6):
        processed, summary = load_reprocessed_qaoa(D)
        record = conditional_record(D, processed, summary)
        assert_finite_record(record)
        conditional_rows.append(record)
        onehot = processed[processed["one_hot"]].copy()
        onehot.to_csv(output / f"d{D}_qaoa_onehot_samples.csv", index=False)
        batches = matched_valid_batches(D, record["one_hot_count"])
        if any(row["batch_size"] != record["one_hot_count"] for row in batches):
            raise ValueError("matched-valid batch size drift")
        matched_rows.extend(batches)
        matched_summaries.append(matched_summary(record, batches))
        raw_path, summary_path, manifest_path = qaoa_input_paths(D)
        inputs.append(
            {
                "D": D,
                "raw_path": str(raw_path.resolve()),
                "raw_sha256": sha256_file(raw_path),
                "recorded_summary_path": str(summary_path.resolve()),
                "recorded_summary_sha256": sha256_file(summary_path),
                "manifest_path": str(manifest_path.resolve()),
                "manifest_sha256": sha256_file(manifest_path),
            }
        )
    conditional_path = write_csv(output / "conditional_metrics.csv", conditional_rows)
    matched_path = write_csv(output / "matched_valid_control.csv", matched_rows)
    matched_summary_path = write_csv(
        output / "matched_valid_summary.csv", matched_summaries
    )
    manifest = {
        "schema_version": "post6a-steps0-2-v1",
        "step": 0,
        "status": "COMPLETE",
        "new_quantum_jobs": 0,
        "near_optimal_absolute_gap_threshold": NEAR_OPTIMAL_GAP,
        "matched_valid_batches_per_D": MATCHED_BATCHES,
        "matched_batch_seed_rule": "9000 + D",
        "inputs": inputs,
        "outputs": {
            "conditional_metrics": sha256_file(conditional_path),
            "matched_valid_control": sha256_file(matched_path),
            "matched_valid_summary": sha256_file(matched_summary_path),
        },
    }
    write_json(output / "manifest.json", manifest)
    print(conditional_path)
    print(matched_summary_path)
    print(json.dumps(matched_summaries, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
