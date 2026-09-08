"""Execute the D=4 structural/fairness gates and verify cost compatibility."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from classiq import calculate_state_vector, sample
from classiq.interface.generator.quantum_program import QuantumProgram
import pandas as pd
from scipy.stats import chisquare

from qera_scaling.classiq_model import make_qmod_cost
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance
from qera_scaling.qubo import (
    assignment_from_bits,
    bits_from_assignment,
    build_energy_spec,
)
from qera_stage6b.provenance import sha256_file, validate_qprog_manifest


WEIGHTS = (1.0 / 3.0,) * 3
INITIAL_SHOTS = 16384
STRUCTURAL_SHOTS = 4096
FAIRNESS_ALPHA = 0.001
TOLERANCE = 1e-10
UNOPTIMIZED_PARAMETERS = {"params": [0.731, 0.419]}


def _load(stem: Path, kind: str) -> tuple[QuantumProgram, dict]:
    qprog_path = stem.with_suffix(".qprog")
    manifest_path = stem.with_suffix(".synthesis.json")
    manifest = validate_qprog_manifest(qprog_path, manifest_path, circuit_kind=kind)
    return (
        QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8")),
        manifest,
    )


def _bits(value) -> tuple[int, ...]:
    return tuple(int(bit) for bit in value)


def _is_one_hot(bits: tuple[int, ...], D: int = 4, K: int = 3) -> bool:
    return all(sum(bits[demand * K : (demand + 1) * K]) == 1 for demand in range(D))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts" / "stage6b"
    output_path = artifacts / "d4" / "d4_correctness_gates.json"
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite Stage 6B evidence: {output_path}")

    init_qprog, init_manifest = _load(
        artifacts / "stateprep" / "d4_initial",
        "d4-independent-dicke-stateprep",
    )
    init_statevector = calculate_state_vector(init_qprog, backend="simulator")
    init_samples = sample(
        init_qprog,
        backend="simulator",
        num_shots=INITIAL_SHOTS,
        random_seed=6640,
    )
    init_statevector_path = artifacts / "stateprep" / "d4_initial_statevector.csv"
    init_samples_path = artifacts / "stateprep" / "d4_initial_samples_raw.csv"
    init_statevector.to_csv(init_statevector_path, index=False)
    init_samples.to_csv(init_samples_path, index=False)

    statevector_rows = [
        (_bits(row.routes), float(row.probability))
        for row in init_statevector.itertuples(index=False)
        if float(row.probability) > TOLERANCE
    ]
    valid_statevector_rows = [
        (bits, probability)
        for bits, probability in statevector_rows
        if _is_one_hot(bits)
    ]
    expected_probability = 1.0 / 81.0
    max_statevector_error = max(
        abs(probability - expected_probability)
        for _, probability in valid_statevector_rows
    )
    invalid_statevector_probability = sum(
        probability for bits, probability in statevector_rows if not _is_one_hot(bits)
    )

    init_total = int(init_samples["counts"].sum())
    init_invalid = sum(
        int(row.counts)
        for row in init_samples.itertuples(index=False)
        if not _is_one_hot(_bits(row.routes))
    )
    observed_by_bits = {
        _bits(row.routes): int(row.counts) for row in init_samples.itertuples(index=False)
    }
    valid_assignments = tuple(ScalingEvaluator(frozen_instance()).all_assignments())
    ordered_bits = [
        bits_from_assignment(ScalingEvaluator(frozen_instance()), assignment)
        for assignment in valid_assignments
    ]
    observed_counts = [observed_by_bits.get(bits, 0) for bits in ordered_bits]
    chi_square, chi_square_p = chisquare(observed_counts)
    empirical_probabilities = [count / init_total for count in observed_counts]
    total_variation = 0.5 * sum(
        abs(probability - expected_probability)
        for probability in empirical_probabilities
    )
    decoded_assignments = {
        assignment_from_bits(ScalingEvaluator(frozen_instance()), bits)
        for bits, _ in valid_statevector_rows
    }
    bit_ordering_pass = decoded_assignments == set(valid_assignments)
    fairness_pass = (
        len(valid_statevector_rows) == 81
        and invalid_statevector_probability <= TOLERANCE
        and max_statevector_error <= TOLERANCE
        and init_total == INITIAL_SHOTS
        and init_invalid == 0
        and float(chi_square_p) >= FAIRNESS_ALPHA
        and bit_ordering_pass
    )

    qaoa_qprog, qaoa_manifest = _load(
        artifacts / "d4" / "constrained_p1",
        "d4-constrained-qaoa-p1",
    )
    structural_statevector = calculate_state_vector(
        qaoa_qprog,
        backend="simulator",
        parameters=UNOPTIMIZED_PARAMETERS,
    )
    structural_samples = sample(
        qaoa_qprog,
        backend="simulator",
        parameters=UNOPTIMIZED_PARAMETERS,
        num_shots=STRUCTURAL_SHOTS,
        random_seed=6641,
    )
    structural_statevector_path = artifacts / "d4" / "unoptimized_statevector.csv"
    structural_samples_path = artifacts / "d4" / "unoptimized_samples_raw.csv"
    structural_statevector.to_csv(structural_statevector_path, index=False)
    structural_samples.to_csv(structural_samples_path, index=False)
    invalid_structural_probability = sum(
        float(row.probability)
        for row in structural_statevector.itertuples(index=False)
        if not _is_one_hot(_bits(row.routes))
    )
    structural_total = int(structural_samples["counts"].sum())
    structural_invalid = sum(
        int(row.counts)
        for row in structural_samples.itertuples(index=False)
        if not _is_one_hot(_bits(row.routes))
    )
    structural_pass = (
        invalid_structural_probability <= TOLERANCE
        and structural_total == STRUCTURAL_SHOTS
        and structural_invalid == 0
    )

    evaluator = ScalingEvaluator(frozen_instance())
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    qmod_cost = make_qmod_cost(spec)
    compatibility_rows = []
    for assignment in evaluator.all_assignments():
        bits = bits_from_assignment(evaluator, assignment)
        frozen_objective = evaluator.weighted_objective(assignment, WEIGHTS, "cost")
        expected_energy = (frozen_objective - spec.phase_offset) / spec.phase_scale
        actual_energy = spec.transformed_energy(bits)
        qmod_classical_energy = float(qmod_cost(bits))
        compatibility_rows.append(
            {
                "assignment": "".join(str(route) for route in assignment),
                "bits": "".join(str(bit) for bit in bits),
                "frozen_objective": frozen_objective,
                "expected_transformed_energy": expected_energy,
                "constrained_transformed_energy": actual_energy,
                "qmod_cost_on_bits": qmod_classical_energy,
                "affine_error": abs(actual_energy - expected_energy),
                "qmod_error": abs(qmod_classical_energy - actual_energy),
            }
        )
    compatibility = pd.DataFrame(compatibility_rows)
    compatibility_path = artifacts / "tables" / "d4_cost_compatibility.csv"
    compatibility_path.parent.mkdir(parents=True, exist_ok=True)
    compatibility.to_csv(compatibility_path, index=False)
    ordering_mismatches = 0
    records = compatibility_rows
    for left_index, left in enumerate(records):
        for right in records[left_index + 1 :]:
            objective_delta = left["frozen_objective"] - right["frozen_objective"]
            energy_delta = (
                left["constrained_transformed_energy"]
                - right["constrained_transformed_energy"]
            )
            if (
                abs(objective_delta) > TOLERANCE
                and abs(energy_delta) > TOLERANCE
                and (objective_delta > 0) != (energy_delta > 0)
            ):
                ordering_mismatches += 1
            if (abs(objective_delta) <= TOLERANCE) != (
                abs(energy_delta) <= TOLERANCE
            ):
                ordering_mismatches += 1
    max_affine_error = float(compatibility["affine_error"].max())
    max_qmod_error = float(compatibility["qmod_error"].max())
    cost_pass = (
        max_affine_error <= TOLERANCE
        and max_qmod_error <= TOLERANCE
        and ordering_mismatches == 0
    )

    all_passed = fairness_pass and structural_pass and cost_pass
    report = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS" if all_passed else "FAIL",
        "fixed_scenario_weights": WEIGHTS,
        "initial_distribution": {
            "status": "PASS" if fairness_pass else "FAIL",
            "qprog_sha256": init_manifest["qprog_sha256"],
            "statevector_valid_support": len(valid_statevector_rows),
            "statevector_invalid_probability": invalid_statevector_probability,
            "statevector_max_abs_error_from_uniform": max_statevector_error,
            "sample_shots": init_total,
            "sample_invalid_shots": init_invalid,
            "sample_chi_square": float(chi_square),
            "sample_chi_square_p_value": float(chi_square_p),
            "fairness_alpha": FAIRNESS_ALPHA,
            "sample_total_variation_from_uniform": total_variation,
            "bit_ordering_verified": bit_ordering_pass,
            "statevector_path": str(init_statevector_path.resolve()),
            "statevector_sha256": sha256_file(init_statevector_path),
            "samples_path": str(init_samples_path.resolve()),
            "samples_sha256": sha256_file(init_samples_path),
        },
        "unoptimized_full_ansatz": {
            "status": "PASS" if structural_pass else "FAIL",
            "parameters": UNOPTIMIZED_PARAMETERS,
            "qprog_sha256": qaoa_manifest["qprog_sha256"],
            "statevector_invalid_probability": invalid_structural_probability,
            "sample_shots": structural_total,
            "sample_invalid_shots": structural_invalid,
            "statevector_path": str(structural_statevector_path.resolve()),
            "statevector_sha256": sha256_file(structural_statevector_path),
            "samples_path": str(structural_samples_path.resolve()),
            "samples_sha256": sha256_file(structural_samples_path),
        },
        "cost_compatibility": {
            "status": "PASS" if cost_pass else "FAIL",
            "assignments_checked": len(compatibility_rows),
            "pairwise_ordering_mismatches": ordering_mismatches,
            "maximum_affine_energy_error": max_affine_error,
            "maximum_qmod_cost_error": max_qmod_error,
            "one_hot_penalty_retained": True,
            "positive_affine_scale": spec.phase_scale,
            "table_path": str(compatibility_path.resolve()),
            "table_sha256": sha256_file(compatibility_path),
        },
    }
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output_path.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    if not all_passed:
        raise RuntimeError("D=4 pre-optimization correctness gate failed")


if __name__ == "__main__":
    main()
