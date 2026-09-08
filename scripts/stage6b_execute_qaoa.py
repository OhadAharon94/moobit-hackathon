"""Execute one already-synthesized Stage 6B constrained-QAOA program."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from importlib.metadata import version
import json
from pathlib import Path
from time import perf_counter

from classiq import ExecutionSession
from classiq.interface.generator.quantum_program import QuantumProgram

from qera.config import FINAL_SHOTS, OPTIMIZER_QUANTILE, OPTIMIZER_SHOTS
from qera_scaling.classiq_model import make_qmod_cost
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance, generate_instance
from qera_scaling.provenance import scaling_spec_sha256
from qera_scaling.qubo import build_energy_spec
from qera_stage6b.provenance import (
    payload_sha256,
    sha256_file,
    source_sha256,
    validate_qprog_manifest,
)


WEIGHTS = (1.0 / 3.0,) * 3
INITIAL_PARAMS = {"params": [0.5, 0.5]}
MAX_ITERATION = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, choices=(4, 6), required=True)
    parser.add_argument("--seed", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.seed < 0:
        raise ValueError("optimizer seed must be nonnegative")
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts" / "stage6b"
    instance = frozen_instance() if args.D == 4 else generate_instance(args.D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    stem = artifacts / f"d{args.D}" / "constrained_p1"
    qprog_path = stem.with_suffix(".qprog")
    synthesis_manifest_path = stem.with_suffix(".synthesis.json")
    circuit_kind = f"d{args.D}-constrained-qaoa-p1"
    circuit_manifest = validate_qprog_manifest(
        qprog_path,
        synthesis_manifest_path,
        circuit_kind=circuit_kind,
    )
    expected_spec_hash = scaling_spec_sha256(spec, "cost", WEIGHTS, 1)
    if circuit_manifest.get("synthesis_spec_sha256") != expected_spec_hash:
        raise ValueError("Stage 6B circuit objective binding mismatch")
    if tuple(circuit_manifest.get("scenario_weights", ())) != WEIGHTS:
        raise ValueError("Stage 6B circuit scenario weights are not frozen uniform weights")
    if int(circuit_manifest.get("qaoa_depth", -1)) != 1:
        raise ValueError("Stage 6B execution is restricted to p=1")

    run_dir = artifacts / f"d{args.D}" / "runs" / f"seed-{args.seed}"
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite Stage 6B run: {run_dir}")
    run_dir.mkdir(parents=True)

    execution_config = {
        "backend": "simulator",
        "D": args.D,
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": WEIGHTS,
        "qaoa_depth": 1,
        "mixer": "three-pair-xy-per-demand",
        "initial_parameters": INITIAL_PARAMS,
        "optimizer_iteration_cap": MAX_ITERATION,
        "optimizer_quantile": OPTIMIZER_QUANTILE,
        "optimizer_shots": OPTIMIZER_SHOTS,
        "final_shots": FINAL_SHOTS,
        "optimizer_seed": args.seed,
    }
    base_manifest = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "classiq_sdk_version": version("classiq"),
        "status": "STARTED",
        "instance_id": instance.instance_id,
        "K": instance.paths_per_demand,
        "S": instance.scenario_count,
        "logical_bits": instance.variable_count,
        **execution_config,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "qprog_path": str(qprog_path.resolve()),
        "qprog_sha256": circuit_manifest["qprog_sha256"],
        "synthesis_manifest_path": str(synthesis_manifest_path.resolve()),
        "synthesis_manifest_sha256": sha256_file(synthesis_manifest_path),
        "synthesis_spec_sha256": expected_spec_hash,
        "synthesis_source_sha256": circuit_manifest["source_sha256"],
        "execution_source_sha256": source_sha256(root),
        "execution_config_sha256": payload_sha256(execution_config),
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(base_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    qprog = QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8"))
    polynomial = make_qmod_cost(spec)

    def cost_function(routes):
        return polynomial(routes)

    started = perf_counter()
    try:
        with ExecutionSession(
            qprog,
            backend="simulator",
            num_shots=OPTIMIZER_SHOTS,
            random_seed=args.seed,
        ) as session:
            trace = session.variational_minimize(
                cost_function=cost_function,
                initial_params=INITIAL_PARAMS,
                max_iteration=MAX_ITERATION,
                quantile=OPTIMIZER_QUANTILE,
                num_shots=OPTIMIZER_SHOTS,
            )
            if not trace:
                raise RuntimeError("Classiq returned an empty optimization trace")
            best_cost, best_params = min(trace, key=lambda item: item[0])
            samples = session.sample(best_params, num_shots=FINAL_SHOTS)
    except Exception as error:
        failure = {
            **base_manifest,
            "status": "EXECUTION_FAILED",
            "execution_runtime_seconds": perf_counter() - started,
            "failure_type": type(error).__name__,
            "failure_message": str(error),
        }
        manifest_path.write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise

    trace_payload = [
        {"iteration": index, "cost": float(cost), "parameters": parameters}
        for index, (cost, parameters) in enumerate(trace)
    ]
    optimizer_path = run_dir / "optimizer.json"
    samples_path = run_dir / "samples_raw.csv"
    optimizer_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    samples.to_csv(samples_path, index=False)
    manifest = {
        **base_manifest,
        "status": "RAW_SAMPLE_SAVED",
        "execution_runtime_seconds": perf_counter() - started,
        "optimizer_trace_length": len(trace_payload),
        "best_cost": float(best_cost),
        "best_parameters": best_params,
        "sample_rows": len(samples),
        "sample_count_sum": int(samples["counts"].sum()),
        "optimizer_sha256": sha256_file(optimizer_path),
        "samples_raw_sha256": sha256_file(samples_path),
        "failure_type": None,
        "failure_message": None,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(run_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
