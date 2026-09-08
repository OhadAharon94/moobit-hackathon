"""Execute one authorized D=6 repeat using the frozen Stage 6A qprog."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter

from classiq import ExecutionSession
from classiq.interface.generator.quantum_program import QuantumProgram

from holy_qow_post6a.common import artifact_root, sha256_file, sha256_payload, write_json
from qera_scaling.classiq_model import make_qmod_cost
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.provenance import validate_scaling_circuit_manifest
from qera_scaling.qubo import build_energy_spec

WEIGHTS = (1.0 / 3.0,) * 3
ALLOWED_NEW_SEEDS = (6201, 6202, 6203, 6204)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, choices=ALLOWED_NEW_SEEDS, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    implementation = Path(__file__).resolve().parents[2]
    stage6a = implementation / "stage6a"
    qprog_path = (
        stage6a
        / "artifacts"
        / "scaling"
        / "circuits"
        / "qera-d6-seed6106-p1.qprog"
    ).resolve()
    synthesis_manifest_path = qprog_path.with_suffix(".synthesis.json")
    gate_path = artifact_root() / "repeatability" / "configuration_gate.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS" or args.seed not in gate["new_optimizer_seeds"]:
        raise ValueError("Step 2 configuration gate is missing, failed, or excludes seed")

    instance = generate_instance(6)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    circuit = validate_scaling_circuit_manifest(
        qprog_path,
        synthesis_manifest_path,
        spec,
        instance.instance_id,
        WEIGHTS,
    )
    if gate["frozen_inputs"]["qprog_sha256"] != circuit["qprog_sha256"]:
        raise ValueError("frozen qprog changed after configuration gate")

    run_dir = artifact_root() / "repeatability" / "runs" / f"seed-{args.seed}"
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing evidence: {run_dir}")
    run_dir.mkdir(parents=True)

    initial_params = {"params": [0.5, 0.5]}
    execution_config = {
        "backend": "simulator",
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": list(WEIGHTS),
        "qaoa_depth": 1,
        "initial_parameters": initial_params,
        "optimizer_iteration_cap": 10,
        "optimizer_quantile": 1.0,
        "optimizer_shots": 512,
        "final_shots": 4096,
        "seed": args.seed,
    }
    base_manifest = {
        "schema_version": "post6a-steps0-2-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "step": 2,
        "status": "STARTED",
        "classiq_sdk_version": version("classiq"),
        "instance_id": instance.instance_id,
        "D": 6,
        "K": 3,
        "S": 3,
        "logical_bits": instance.variable_count,
        **execution_config,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "energy_range_mode": spec.range_mode,
        "qprog_path": str(qprog_path),
        "qprog_sha256": circuit["qprog_sha256"],
        "synthesis_manifest_path": str(synthesis_manifest_path),
        "synthesis_manifest_sha256": sha256_file(synthesis_manifest_path),
        "synthesis_spec_sha256": circuit["synthesis_spec_sha256"],
        "configuration_gate_path": str(gate_path.resolve()),
        "configuration_gate_sha256": sha256_file(gate_path),
        "execution_script_sha256": sha256_file(Path(__file__)),
        "execution_config_sha256": sha256_payload(execution_config),
    }
    manifest_path = run_dir / "manifest.json"
    write_json(manifest_path, base_manifest)

    qprog = QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8"))
    polynomial = make_qmod_cost(spec)

    def cost_function(routes):
        return polynomial(routes)

    started = perf_counter()
    try:
        with ExecutionSession(
            qprog,
            backend="simulator",
            num_shots=512,
            random_seed=args.seed,
        ) as session:
            trace = session.variational_minimize(
                cost_function=cost_function,
                initial_params=initial_params,
                max_iteration=10,
                quantile=1.0,
                num_shots=512,
            )
            if not trace:
                raise RuntimeError("Classiq returned an empty optimization trace")
            best_cost, best_params = min(trace, key=lambda item: item[0])
            samples = session.sample(best_params, num_shots=4096)
    except Exception as error:
        failure = {
            **base_manifest,
            "status": "EXECUTION_FAILED",
            "execution_runtime_seconds": perf_counter() - started,
            "failure_type": type(error).__name__,
            "failure_message": str(error),
        }
        write_json(manifest_path, failure)
        raise

    trace_payload = [
        {"iteration": index, "cost": float(cost), "parameters": parameters}
        for index, (cost, parameters) in enumerate(trace)
    ]
    optimizer_path = run_dir / "optimizer.json"
    write_json(optimizer_path, trace_payload)
    samples_path = run_dir / "samples_raw.csv"
    samples.to_csv(samples_path, index=False)
    manifest = {
        **base_manifest,
        "status": "RAW_SAMPLE_SAVED",
        "execution_runtime_seconds": perf_counter() - started,
        "optimizer_trace_length": len(trace_payload),
        "best_cost": float(best_cost),
        "best_parameters": best_params,
        "sample_rows": len(samples),
        "optimizer_sha256": sha256_file(optimizer_path),
        "samples_raw_sha256": sha256_file(samples_path),
    }
    write_json(manifest_path, manifest)
    print(run_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
