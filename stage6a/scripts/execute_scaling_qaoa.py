"""Optimize and sample one already-synthesized Stage 6A QAOA program."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
from time import perf_counter

from classiq import ExecutionSession
from classiq.interface.generator.quantum_program import QuantumProgram

from qera.config import FINAL_SHOTS, OPTIMIZER_QUANTILE, OPTIMIZER_SHOTS
from qera_scaling.classiq_model import make_qmod_cost
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.provenance import (
    sha256_file,
    source_sha256,
    validate_scaling_circuit_manifest,
)
from qera_scaling.qubo import build_energy_spec

WEIGHTS = (1.0 / 3.0,) * 3
SAFE_RUN_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _recorded_path(path: Path, repository_root: Path) -> str:
    """Prefer a portable repository-relative path for committed artifacts."""

    try:
        return path.relative_to(repository_root).as_posix()
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, choices=(5, 6), required=True)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--qprog", type=Path, default=None)
    parser.add_argument("--synthesis-manifest", type=Path, default=None)
    parser.add_argument("--initial-params", type=float, nargs=2, default=(0.5, 0.5))
    parser.add_argument("--max-iteration", type=int, default=10)
    parser.add_argument("--optimizer-shots", type=int, default=OPTIMIZER_SHOTS)
    parser.add_argument("--final-shots", type=int, default=FINAL_SHOTS)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_iteration < 1 or args.optimizer_shots < 1 or args.final_shots < 1:
        raise ValueError("iteration and shot budgets must be positive")
    if len(args.initial_params) != 2:
        raise ValueError("p=1 requires exactly two initial parameters")

    stage6a_root = Path(__file__).resolve().parents[1]
    implementation_root = stage6a_root.parent
    instance = generate_instance(args.D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    stem = f"{instance.instance_id}-p1"
    circuit_dir = stage6a_root / "artifacts" / "scaling" / "circuits"
    qprog_path = (args.qprog or circuit_dir / f"{stem}.qprog").resolve()
    synthesis_manifest_path = (
        args.synthesis_manifest or circuit_dir / f"{stem}.synthesis.json"
    ).resolve()
    circuit_manifest = validate_scaling_circuit_manifest(
        qprog_path, synthesis_manifest_path, spec, instance.instance_id, WEIGHTS
    )

    run_name = args.run_name or f"{stem}-uniform-cost"
    if not SAFE_RUN_NAME.fullmatch(run_name):
        raise ValueError("run name may contain only letters, digits, dot, underscore, and dash")
    run_dir = stage6a_root / "artifacts" / "scaling" / "qaoa" / run_name
    if run_dir.exists():
        raise FileExistsError(
            f"refusing to overwrite existing run directory; choose --run-name: {run_dir}"
        )
    run_dir.mkdir(parents=True)

    seed = instance.seed if args.seed is None else args.seed
    initial_params = {"params": [float(value) for value in args.initial_params]}
    execution_config = {
        "backend": "simulator",
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": WEIGHTS,
        "qaoa_depth": 1,
        "initial_parameters": initial_params,
        "optimizer_iteration_cap": args.max_iteration,
        "optimizer_quantile": OPTIMIZER_QUANTILE,
        "optimizer_shots": args.optimizer_shots,
        "final_shots": args.final_shots,
        "seed": seed,
    }
    base_manifest = {
        "schema_version": "stage6a-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "classiq_sdk_version": version("classiq"),
        "instance_id": instance.instance_id,
        "D": instance.demand_count,
        "K": instance.paths_per_demand,
        "S": instance.scenario_count,
        "logical_bits": instance.variable_count,
        **execution_config,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "energy_range_mode": spec.range_mode,
        "qprog_path": _recorded_path(qprog_path, implementation_root),
        "qprog_sha256": circuit_manifest["qprog_sha256"],
        "synthesis_spec_sha256": circuit_manifest["synthesis_spec_sha256"],
        "synthesis_manifest_path": _recorded_path(
            synthesis_manifest_path, implementation_root
        ),
        "synthesis_manifest_sha256": sha256_file(synthesis_manifest_path),
        "synthesis_source_sha256": circuit_manifest["source_sha256"],
        "execution_source_sha256": source_sha256(implementation_root, stage6a_root),
        "execution_config_sha256": _payload_sha256(execution_config),
    }

    qprog = QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8"))
    polynomial = make_qmod_cost(spec)

    def cost_function(routes):
        return polynomial(routes)

    started = perf_counter()
    try:
        with ExecutionSession(
            qprog,
            backend="simulator",
            num_shots=args.optimizer_shots,
            random_seed=seed,
        ) as session:
            trace = session.variational_minimize(
                cost_function=cost_function,
                initial_params=initial_params,
                max_iteration=args.max_iteration,
                quantile=OPTIMIZER_QUANTILE,
                num_shots=args.optimizer_shots,
            )
            if not trace:
                raise RuntimeError("Classiq returned an empty optimization trace")
            best_cost, best_params = min(trace, key=lambda item: item[0])
            samples = session.sample(best_params, num_shots=args.final_shots)
    except Exception as error:
        failure = {
            **base_manifest,
            "status": "EXECUTION_FAILED",
            "execution_runtime_seconds": perf_counter() - started,
            "failure_type": type(error).__name__,
            "failure_message": str(error),
        }
        (run_dir / "manifest.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        raise

    trace_payload = [
        {"iteration": index, "cost": float(cost), "parameters": parameters}
        for index, (cost, parameters) in enumerate(trace)
    ]
    optimizer_path = run_dir / "optimizer.json"
    optimizer_path.write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    samples_path = run_dir / "samples_raw.csv"
    samples.to_csv(samples_path, index=False, lineterminator="\n")
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
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(run_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
