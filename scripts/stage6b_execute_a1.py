"""Execute only the Stage 6B single-demand correctness circuits."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter

from classiq import calculate_state_vector, sample
from classiq.interface.generator.quantum_program import QuantumProgram

from qera_stage6b.provenance import sha256_file, validate_qprog_manifest


ANGLES = (0.173, 0.417, 0.911, 1.337)
SHOTS = 4096
TOLERANCE = 1e-10


def _load_bound_qprog(stem: Path, circuit_kind: str) -> tuple[QuantumProgram, dict]:
    qprog_path = stem.with_suffix(".qprog")
    manifest_path = stem.with_suffix(".synthesis.json")
    manifest = validate_qprog_manifest(
        qprog_path,
        manifest_path,
        circuit_kind=circuit_kind,
    )
    qprog = QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8"))
    return qprog, manifest


def _bits(value) -> tuple[int, ...]:
    return tuple(int(bit) for bit in value)


def _statevector_metrics(frame) -> dict:
    probabilities = {
        _bits(row.routes): float(row.probability)
        for row in frame.itertuples(index=False)
        if float(row.probability) > TOLERANCE
    }
    invalid_probability = sum(
        probability for bits, probability in probabilities.items() if sum(bits) != 1
    )
    return {
        "nonzero_probabilities": {
            "".join(str(bit) for bit in bits): probability
            for bits, probability in sorted(probabilities.items())
        },
        "probability_sum": sum(probabilities.values()),
        "invalid_hamming_weight_probability": invalid_probability,
        "one_hot_probability": 1.0 - invalid_probability,
    }


def _sample_metrics(frame) -> dict:
    total = int(frame["counts"].sum())
    invalid = sum(
        int(row.counts)
        for row in frame.itertuples(index=False)
        if sum(_bits(row.routes)) != 1
    )
    return {
        "shots": total,
        "invalid_shots": invalid,
        "one_hot_probability": (total - invalid) / total,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifact_root = root / "artifacts" / "stage6b"
    stateprep_report_path = artifact_root / "stage6b_stateprep_validation.json"
    mixer_report_path = artifact_root / "stage6b_mixer_preservation.json"
    for path in (stateprep_report_path, mixer_report_path):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite Stage 6B evidence: {path}")

    started = perf_counter()
    stateprep_stem = artifact_root / "stateprep" / "single_demand"
    stateprep_qprog, stateprep_manifest = _load_bound_qprog(
        stateprep_stem,
        "single-demand-dicke-stateprep",
    )
    statevector = calculate_state_vector(stateprep_qprog, backend="simulator")
    samples = sample(
        stateprep_qprog,
        backend="simulator",
        num_shots=SHOTS,
        random_seed=6600,
    )
    statevector_path = artifact_root / "stateprep" / "single_demand_statevector.csv"
    samples_path = artifact_root / "stateprep" / "single_demand_samples_raw.csv"
    statevector.to_csv(statevector_path, index=False)
    samples.to_csv(samples_path, index=False)
    stateprep_exact = _statevector_metrics(statevector)
    stateprep_sampled = _sample_metrics(samples)
    expected_states = {"001", "010", "100"}
    stateprep_passed = (
        set(stateprep_exact["nonzero_probabilities"]) == expected_states
        and abs(stateprep_exact["probability_sum"] - 1.0) <= TOLERANCE
        and all(
            abs(probability - 1.0 / 3.0) <= TOLERANCE
            for probability in stateprep_exact["nonzero_probabilities"].values()
        )
        and stateprep_sampled["shots"] == SHOTS
        and stateprep_sampled["invalid_shots"] == 0
    )
    stateprep_report = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "classiq_sdk_version": version("classiq"),
        "status": "PASS" if stateprep_passed else "FAIL",
        "circuit_kind": stateprep_manifest["circuit_kind"],
        "qprog_sha256": stateprep_manifest["qprog_sha256"],
        "statevector": stateprep_exact,
        "sampled": stateprep_sampled,
        "expected_states": sorted(expected_states),
        "expected_probability_per_state": 1.0 / 3.0,
        "statevector_path": str(statevector_path.resolve()),
        "statevector_sha256": sha256_file(statevector_path),
        "samples_path": str(samples_path.resolve()),
        "samples_sha256": sha256_file(samples_path),
    }
    stateprep_report_path.write_text(
        json.dumps(stateprep_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not stateprep_passed:
        raise RuntimeError("single-demand Dicke state-preparation gate failed")

    trials = []
    all_passed = True
    for initial_route in range(3):
        stem = artifact_root / "mixer_validation" / f"basis-{initial_route}"
        qprog, manifest = _load_bound_qprog(
            stem,
            f"single-demand-xy-mixer-basis-{initial_route}",
        )
        parameters = [{"beta": angle} for angle in ANGLES]
        statevectors = calculate_state_vector(
            qprog,
            backend="simulator",
            parameters=parameters,
        )
        sample_frames = sample(
            qprog,
            backend="simulator",
            parameters=parameters,
            num_shots=SHOTS,
            random_seed=6610 + initial_route,
        )
        if len(statevectors) != len(ANGLES) or len(sample_frames) != len(ANGLES):
            raise RuntimeError("Classiq batch result length does not match angle sweep")
        for index, angle in enumerate(ANGLES):
            statevector_path = artifact_root / "mixer_validation" / (
                f"basis-{initial_route}-angle-{index}-statevector.csv"
            )
            samples_path = artifact_root / "mixer_validation" / (
                f"basis-{initial_route}-angle-{index}-samples_raw.csv"
            )
            statevectors[index].to_csv(statevector_path, index=False)
            sample_frames[index].to_csv(samples_path, index=False)
            exact = _statevector_metrics(statevectors[index])
            sampled = _sample_metrics(sample_frames[index])
            passed = (
                abs(exact["probability_sum"] - 1.0) <= TOLERANCE
                and exact["invalid_hamming_weight_probability"] <= TOLERANCE
                and sampled["shots"] == SHOTS
                and sampled["invalid_shots"] == 0
            )
            all_passed = all_passed and passed
            trials.append(
                {
                    "initial_route": initial_route,
                    "beta": angle,
                    "status": "PASS" if passed else "FAIL",
                    "qprog_sha256": manifest["qprog_sha256"],
                    "statevector": exact,
                    "sampled": sampled,
                    "statevector_path": str(statevector_path.resolve()),
                    "statevector_sha256": sha256_file(statevector_path),
                    "samples_path": str(samples_path.resolve()),
                    "samples_sha256": sha256_file(samples_path),
                }
            )
    mixer_report = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "classiq_sdk_version": version("classiq"),
        "status": "PASS" if all_passed else "FAIL",
        "angles": ANGLES,
        "basis_states_tested": [0, 1, 2],
        "trial_count": len(trials),
        "shots_per_trial": SHOTS,
        "total_sampled_shots": len(trials) * SHOTS,
        "mathematical_pair_unitary": "exp[-i beta (XX + YY)]",
        "pair_decomposition": "RXX(2*beta) then RYY(2*beta)",
        "pair_order": [[0, 1], [1, 2], [0, 2]],
        "tolerance": TOLERANCE,
        "execution_runtime_seconds": perf_counter() - started,
        "trials": trials,
    }
    mixer_report_path.write_text(
        json.dumps(mixer_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(stateprep_report_path.resolve())
    print(mixer_report_path.resolve())
    print(json.dumps({"stateprep": stateprep_report["status"], "mixer": mixer_report["status"]}, indent=2))
    if not all_passed:
        raise RuntimeError("single-demand XY mixer preservation gate failed")


if __name__ == "__main__":
    main()
