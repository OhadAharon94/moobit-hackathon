"""Optimize and sample an already synthesized Q-ERA qprog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from classiq import ExecutionSession
from classiq.interface.generator.quantum_program import QuantumProgram

from qera.config import (
    DEFAULT_SEED,
    FINAL_SHOTS,
    INITIAL_SCENARIO_WEIGHTS,
    OPTIMIZER_QUANTILE,
    OPTIMIZER_SHOTS,
    PLAN_VERSION,
    SCHEMA_VERSION,
)
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.qaoa_model import make_qmod_cost


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--objective-mode", choices=("cost", "regret"), default="cost")
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--weights", type=float, nargs=3, default=INITIAL_SCENARIO_WEIGHTS)
    parser.add_argument("--initial-params", type=float, nargs=2, default=(0.5, 0.5))
    parser.add_argument(
        "--qprog",
        type=Path,
        default=None,
    )
    parser.add_argument("--max-iteration", type=int, default=10)
    parser.add_argument("--optimizer-shots", type=int, default=OPTIMIZER_SHOTS)
    parser.add_argument("--final-shots", type=int, default=FINAL_SHOTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights = tuple(args.weights)
    if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-8:
        raise ValueError("scenario weights must be nonnegative and sum to one")
    implementation_root = Path(__file__).resolve().parents[1]
    qprog_path = args.qprog or (
        implementation_root
        / "artifacts"
        / "circuits"
        / f"uniform_{args.objective_mode}_p1.qprog"
    )
    run_name = args.run_name or f"uniform_{args.objective_mode}_p1_smoke"
    if not qprog_path.exists():
        raise FileNotFoundError(
            f"missing synthesized qprog: {qprog_path}; run synthesize_qaoa.py first"
        )

    run_dir = implementation_root / "artifacts" / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    spec = build_energy_spec(
        Evaluator(), weights, args.objective_mode, energy_mode="base"
    )
    polynomial = make_qmod_cost(spec)

    def cost_function(routes):
        return polynomial(routes)

    initial_params = {"params": list(args.initial_params)}
    qprog = QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8"))
    with ExecutionSession(
        qprog,
        backend="simulator",
        num_shots=args.optimizer_shots,
        random_seed=args.seed,
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

    trace_payload = [
        {"iteration": index, "cost": float(cost), "parameters": parameters}
        for index, (cost, parameters) in enumerate(trace)
    ]
    (run_dir / "optimizer.json").write_text(
        json.dumps(trace_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    samples.to_csv(run_dir / "samples_raw.csv", index=False)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "plan_version": PLAN_VERSION,
        "status": "RAW_SAMPLE_SAVED",
        "backend": "simulator",
        "objective_mode": args.objective_mode,
        "energy_mode": "base",
        "scenario_weights": weights,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "seed": args.seed,
        "optimizer_shots": args.optimizer_shots,
        "final_shots": args.final_shots,
        "optimizer_iteration_cap": args.max_iteration,
        "optimizer_trace_length": len(trace_payload),
        "initial_parameters": initial_params,
        "best_cost": float(best_cost),
        "best_parameters": best_params,
        "sample_rows": len(samples),
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(run_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
