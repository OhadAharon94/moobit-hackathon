"""Post-process five D=6 optimizer seeds and their matched controls."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from holy_qow_post6a.common import artifact_root, sha256_file, write_csv, write_json
from holy_qow_post6a.conditional import (
    MATCHED_BATCHES,
    NEAR_OPTIMAL_GAP,
    matched_summary,
    matched_valid_batches,
)
from holy_qow_post6a.repeatability import (
    CONTROL_OFFSETS,
    REPEAT_SEEDS,
    aggregate_optimizer_seed_variability,
    load_manifest,
    optimizer_trace_rows,
    probability_record,
    run_paths,
)
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.postprocess import (
    process_sample_frame,
    random_bitstring_frame,
    random_valid_route_frame,
)
from qera_scaling.provenance import validate_scaling_circuit_manifest
from qera_scaling.qubo import build_energy_spec

WEIGHTS = (1.0 / 3.0,) * 3
AGGREGATE_METRICS = (
    "p_one_hot",
    "p_joint_feasible",
    "p_near_optimal",
    "p_feasible_given_onehot",
    "p_near_optimal_given_onehot",
    "best_feasible_objective_gap",
    "best_feasible_worst_case_regret",
    "best_feasible_regret_gap",
)


def _one_sided_sign_pvalue(wins: int, losses: int) -> float:
    trials = wins + losses
    if trials == 0:
        return 1.0
    return sum(math.comb(trials, k) for k in range(wins, trials + 1)) / (2**trials)


def _validate_run(seed: int, expected: dict, evaluator, spec) -> tuple[dict, Path, Path]:
    manifest_path, raw_path, optimizer_path = run_paths(seed)
    manifest = load_manifest(seed)
    if manifest.get("status") not in {"RAW_SAMPLE_SAVED", "PROCESSED"}:
        raise ValueError(f"seed {seed} does not contain successful raw evidence")
    if int(manifest["seed"]) != seed:
        raise ValueError(f"seed {seed} manifest seed mismatch")
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"seed {seed} changed frozen configuration field {key}")
    if manifest["samples_raw_sha256"] != sha256_file(raw_path):
        raise ValueError(f"seed {seed} raw sample hash mismatch")
    if manifest["optimizer_sha256"] != sha256_file(optimizer_path):
        raise ValueError(f"seed {seed} optimizer trace hash mismatch")
    validate_scaling_circuit_manifest(
        Path(manifest["qprog_path"]),
        Path(manifest["synthesis_manifest_path"]),
        spec,
        evaluator.instance.instance_id,
        WEIGHTS,
    )
    return manifest, raw_path, optimizer_path


def main() -> None:
    output = artifact_root() / "repeatability"
    gate_path = output / "configuration_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise ValueError("Step 2 configuration gate did not pass")
    expected = gate["expected_configuration"]
    evaluator = ScalingEvaluator(generate_instance(6))
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    synthesis = json.loads(
        Path(gate["frozen_inputs"]["synthesis_manifest_path"]).read_text(
            encoding="utf-8"
        )
    )

    records = []
    matched_rows = []
    matched_summaries = []
    trace_rows = []
    inputs = []
    for seed in REPEAT_SEEDS:
        manifest, raw_path, optimizer_path = _validate_run(
            seed, expected, evaluator, spec
        )
        shots = int(manifest["final_shots"])
        control_seeds = {
            name: seed + offset for name, offset in CONTROL_OFFSETS.items()
        }
        frames = {
            "qaoa": (pd.read_csv(raw_path), None),
            "uniform_random_bitstrings": (
                random_bitstring_frame(
                    evaluator.instance.variable_count,
                    shots,
                    control_seeds["uniform_random_bitstrings"],
                ),
                control_seeds["uniform_random_bitstrings"],
            ),
            "uniform_random_valid_routes": (
                random_valid_route_frame(
                    evaluator,
                    shots,
                    control_seeds["uniform_random_valid_routes"],
                ),
                control_seeds["uniform_random_valid_routes"],
            ),
        }
        seed_output = output / "processed" / f"seed-{seed}"
        control_output = output / "controls" / f"seed-{seed}"
        qaoa_record = None
        for method, (frame, random_seed) in frames.items():
            processed, summary = process_sample_frame(
                frame,
                evaluator,
                spec,
                WEIGHTS,
                declared_shots=shots,
                approximation_threshold=NEAR_OPTIMAL_GAP,
            )
            record = probability_record(
                processed,
                summary,
                optimizer_seed=seed,
                method=method,
                random_seed=random_seed,
            )
            records.append(record)
            if method == "qaoa":
                qaoa_record = record
                target = seed_output
            else:
                target = control_output / method
                target.mkdir(parents=True, exist_ok=True)
                frame.to_csv(target / "samples_raw.csv", index=False)
            target.mkdir(parents=True, exist_ok=True)
            processed.to_csv(target / "samples.csv", index=False)
            write_json(target / "summary.json", summary)

        if qaoa_record is None or qaoa_record["one_hot_count"] <= 0:
            raise ValueError(f"seed {seed} has no one-hot samples for matched analysis")
        batches = matched_valid_batches(
            6,
            int(qaoa_record["one_hot_count"]),
            batches=MATCHED_BATCHES,
            seed=control_seeds["matched_random_valid_batches"],
        )
        for row in batches:
            row["optimizer_seed"] = seed
            row["control_random_seed"] = control_seeds[
                "matched_random_valid_batches"
            ]
        matched_rows.extend(batches)
        matched = matched_summary(qaoa_record, batches)
        matched["optimizer_seed"] = seed
        matched["control_random_seed"] = control_seeds[
            "matched_random_valid_batches"
        ]
        matched_summaries.append(matched)
        trace = json.loads(optimizer_path.read_text(encoding="utf-8"))
        trace_rows.extend(optimizer_trace_rows(seed, trace))
        inputs.append(
            {
                "optimizer_seed": seed,
                "manifest_path": str((run_paths(seed)[0]).resolve()),
                "manifest_sha256": sha256_file(run_paths(seed)[0]),
                "raw_path": str(raw_path.resolve()),
                "raw_sha256": sha256_file(raw_path),
                "optimizer_path": str(optimizer_path.resolve()),
                "optimizer_sha256": sha256_file(optimizer_path),
                "execution_runtime_seconds": manifest[
                    "execution_runtime_seconds"
                ],
                "optimizer_trace_length": manifest["optimizer_trace_length"],
                "best_reported_optimizer_cost": manifest["best_cost"],
                "best_parameters": manifest["best_parameters"],
                "status": manifest["status"],
                "warning": manifest.get("warning"),
            }
        )

    for record in records:
        record.update(
            {
                "synthesized_qubits": synthesis["synthesized_qubits"],
                "circuit_depth": synthesis["depth"],
                "gate_count": synthesis["gate_count"],
                "two_qubit_gate_count": synthesis["two_qubit_gate_count"],
            }
        )
        matching = next(
            item for item in inputs if item["optimizer_seed"] == record["optimizer_seed"]
        )
        record["execution_runtime_seconds"] = matching[
            "execution_runtime_seconds"
        ]
        record["optimizer_trace_length"] = matching["optimizer_trace_length"]
        record["best_reported_optimizer_cost"] = matching[
            "best_reported_optimizer_cost"
        ]
        record["execution_status"] = matching["status"]
        record["execution_warning"] = matching["warning"]
        record["synthesis_warning"] = synthesis.get("warning")

    metrics_path = write_csv(output / "d6_repeatability.csv", records)
    aggregate = aggregate_optimizer_seed_variability(records, AGGREGATE_METRICS)
    aggregate_path = write_csv(output / "d6_seed_level_summary.csv", aggregate)
    matched_path = write_csv(output / "d6_matched_valid_control.csv", matched_rows)
    matched_summary_path = write_csv(
        output / "d6_matched_valid_summary.csv", matched_summaries
    )
    trace_path = write_csv(output / "optimizer_traces.csv", trace_rows)
    records_by_key = {
        (int(record["optimizer_seed"]), record["method"]): record
        for record in records
    }
    matched_by_seed = {
        int(record["optimizer_seed"]): record for record in matched_summaries
    }
    comparison_rows = []
    for seed in REPEAT_SEEDS:
        qaoa = records_by_key[(seed, "qaoa")]
        bit = records_by_key[(seed, "uniform_random_bitstrings")]
        valid = records_by_key[(seed, "uniform_random_valid_routes")]
        matched = matched_by_seed[seed]
        comparison_rows.append(
            {
                "optimizer_seed": seed,
                "qaoa_to_random_bit_onehot_ratio": (
                    qaoa["p_one_hot"] / bit["p_one_hot"]
                    if bit["p_one_hot"]
                    else None
                ),
                "qaoa_to_random_bit_joint_feasible_ratio": (
                    qaoa["p_joint_feasible"] / bit["p_joint_feasible"]
                    if bit["p_joint_feasible"]
                    else None
                ),
                "qaoa_minus_random_valid_conditional_feasible": (
                    qaoa["p_feasible_given_onehot"]
                    - valid["p_feasible_given_onehot"]
                ),
                "qaoa_minus_random_valid_conditional_near": (
                    qaoa["p_near_optimal_given_onehot"]
                    - valid["p_near_optimal_given_onehot"]
                ),
                "qaoa_minus_random_bit_best_objective_gap": (
                    qaoa["best_feasible_objective_gap"]
                    - bit["best_feasible_objective_gap"]
                ),
                "qaoa_minus_random_bit_best_worst_case_regret": (
                    qaoa["best_feasible_worst_case_regret"]
                    - bit["best_feasible_worst_case_regret"]
                ),
                "matched_batch_size": matched["matched_batch_size"],
                "p_random_best_gap_at_least_as_good": matched[
                    "empirical_p_random_best_gap_at_least_as_good"
                ],
                "p_random_best_regret_at_least_as_good": matched[
                    "empirical_p_random_best_regret_at_least_as_good"
                ],
                "p_random_feasible_fraction_at_least_as_high": matched[
                    "empirical_p_random_feasible_fraction_at_least_as_high"
                ],
                "p_random_near_fraction_at_least_as_high": matched[
                    "empirical_p_random_near_fraction_at_least_as_high"
                ],
            }
        )
    comparison_path = write_csv(
        output / "d6_control_comparison.csv", comparison_rows
    )
    qaoa_rows = [
        records_by_key[(seed, "qaoa")] for seed in REPEAT_SEEDS
    ]
    bit_rows = [
        records_by_key[(seed, "uniform_random_bitstrings")] for seed in REPEAT_SEEDS
    ]
    onehot_wins = sum(
        left["p_one_hot"] > right["p_one_hot"]
        for left, right in zip(qaoa_rows, bit_rows, strict=True)
    )
    joint_wins = sum(
        left["p_joint_feasible"] > right["p_joint_feasible"]
        for left, right in zip(qaoa_rows, bit_rows, strict=True)
    )
    best_gap_wins = sum(
        left["best_feasible_objective_gap"]
        < right["best_feasible_objective_gap"]
        for left, right in zip(qaoa_rows, bit_rows, strict=True)
    )
    best_regret_wins = sum(
        left["best_feasible_worst_case_regret"]
        < right["best_feasible_worst_case_regret"]
        for left, right in zip(qaoa_rows, bit_rows, strict=True)
    )
    comparison_summary = {
        "qaoa_mean_onehot_probability": sum(row["p_one_hot"] for row in qaoa_rows)
        / len(qaoa_rows),
        "random_bit_mean_onehot_probability": sum(
            row["p_one_hot"] for row in bit_rows
        )
        / len(bit_rows),
        "qaoa_to_random_bit_mean_onehot_ratio": (
            sum(row["p_one_hot"] for row in qaoa_rows)
            / sum(row["p_one_hot"] for row in bit_rows)
        ),
        "qaoa_mean_joint_feasible_probability": sum(
            row["p_joint_feasible"] for row in qaoa_rows
        )
        / len(qaoa_rows),
        "random_bit_mean_joint_feasible_probability": sum(
            row["p_joint_feasible"] for row in bit_rows
        )
        / len(bit_rows),
        "qaoa_to_random_bit_mean_joint_feasible_ratio": (
            sum(row["p_joint_feasible"] for row in qaoa_rows)
            / sum(row["p_joint_feasible"] for row in bit_rows)
        ),
        "onehot_probability_pairwise_wins": onehot_wins,
        "onehot_probability_pairwise_trials": len(REPEAT_SEEDS),
        "onehot_probability_one_sided_sign_pvalue": _one_sided_sign_pvalue(
            onehot_wins, len(REPEAT_SEEDS) - onehot_wins
        ),
        "joint_feasible_probability_pairwise_wins": joint_wins,
        "joint_feasible_probability_pairwise_trials": len(REPEAT_SEEDS),
        "joint_feasible_probability_one_sided_sign_pvalue": _one_sided_sign_pvalue(
            joint_wins, len(REPEAT_SEEDS) - joint_wins
        ),
        "best_objective_gap_pairwise_wins_over_random_bits": best_gap_wins,
        "best_objective_gap_pairwise_trials": len(REPEAT_SEEDS),
        "best_objective_gap_one_sided_sign_pvalue": _one_sided_sign_pvalue(
            best_gap_wins, len(REPEAT_SEEDS) - best_gap_wins
        ),
        "best_worst_case_regret_pairwise_wins_over_random_bits": best_regret_wins,
        "best_worst_case_regret_pairwise_trials": len(REPEAT_SEEDS),
        "best_worst_case_regret_one_sided_sign_pvalue": _one_sided_sign_pvalue(
            best_regret_wins, len(REPEAT_SEEDS) - best_regret_wins
        ),
        "qaoa_conditional_feasible_above_random_valid_seeds": sum(
            row["qaoa_minus_random_valid_conditional_feasible"] > 0
            for row in comparison_rows
        ),
        "qaoa_conditional_near_above_random_valid_seeds": sum(
            row["qaoa_minus_random_valid_conditional_near"] > 0
            for row in comparison_rows
        ),
        "matched_best_gap_p_below_0_05_seeds": sum(
            row["p_random_best_gap_at_least_as_good"] < 0.05
            for row in comparison_rows
        ),
        "matched_best_regret_p_below_0_05_seeds": sum(
            row["p_random_best_regret_at_least_as_good"] < 0.05
            for row in comparison_rows
        ),
        "matched_conditional_feasible_p_below_0_05_seeds": sum(
            row["p_random_feasible_fraction_at_least_as_high"] < 0.05
            for row in comparison_rows
        ),
        "matched_conditional_near_p_below_0_05_seeds": sum(
            row["p_random_near_fraction_at_least_as_high"] < 0.05
            for row in comparison_rows
        ),
    }
    comparison_summary_path = write_json(
        output / "d6_control_comparison_summary.json", comparison_summary
    )
    manifest = {
        "schema_version": "post6a-steps0-2-v1",
        "step": 2,
        "status": "COMPLETE",
        "optimizer_seed_count": len(REPEAT_SEEDS),
        "optimizer_seeds": list(REPEAT_SEEDS),
        "original_stage6a_seed_reused": 6106,
        "new_quantum_jobs": len(REPEAT_SEEDS) - 1,
        "frozen_configuration": expected,
        "near_optimal_absolute_gap_threshold": NEAR_OPTIMAL_GAP,
        "matched_valid_batches_per_seed": MATCHED_BATCHES,
        "finite_shot_uncertainty": "per-seed Wilson score intervals, 95%",
        "optimizer_seed_uncertainty": (
            "mean/sample SD/median/IQR/range over five seed-level point estimates; "
            "not pooled across shots"
        ),
        "circuit_resources": {
            "qubits": synthesis["synthesized_qubits"],
            "depth": synthesis["depth"],
            "gates": synthesis["gate_count"],
            "two_qubit_gates": synthesis["two_qubit_gate_count"],
        },
        "configuration_gate_sha256": sha256_file(gate_path),
        "inputs": inputs,
        "outputs": {
            "repeatability": sha256_file(metrics_path),
            "seed_level_summary": sha256_file(aggregate_path),
            "matched_valid_control": sha256_file(matched_path),
            "matched_valid_summary": sha256_file(matched_summary_path),
            "optimizer_traces": sha256_file(trace_path),
            "control_comparison": sha256_file(comparison_path),
            "control_comparison_summary": sha256_file(comparison_summary_path),
        },
    }
    manifest_path = write_json(output / "manifest.json", manifest)
    print(manifest_path)
    print(pd.DataFrame(records).query("method == 'qaoa'").to_string(index=False))
    print(pd.DataFrame(matched_summaries).to_string(index=False))
    print(pd.DataFrame(aggregate).to_string(index=False))
    print(json.dumps(comparison_summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
