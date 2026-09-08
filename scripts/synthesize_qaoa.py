"""Synthesize the Stage 3 uniform-cost p=1 QAOA model and save evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from classiq import get_transpiled_circuit_metrics, synthesize

from qera.config import INITIAL_SCENARIO_WEIGHTS, PLAN_VERSION, SCHEMA_VERSION
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.qaoa_model import build_qaoa_main


def _metrics_payload(metrics: Any) -> dict[str, Any]:
    count_ops = getattr(metrics, "count_ops", None)
    return {
        "width": getattr(metrics, "width", None),
        "depth": getattr(metrics, "depth", None),
        "count_ops": dict(count_ops) if count_ops is not None else None,
    }


def main() -> None:
    implementation_root = Path(__file__).resolve().parents[1]
    circuit_dir = implementation_root / "artifacts" / "circuits"
    circuit_dir.mkdir(parents=True, exist_ok=True)

    spec = build_energy_spec(
        Evaluator(), INITIAL_SCENARIO_WEIGHTS, "cost", energy_mode="base"
    )
    main_model = build_qaoa_main(spec, depth=1)
    qprog = synthesize(main_model)
    qprog_path = circuit_dir / "uniform_cost_p1.qprog"
    qprog_path.write_text(str(qprog), encoding="utf-8")

    metrics = get_transpiled_circuit_metrics(qprog)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "plan_version": PLAN_VERSION,
        "objective_mode": "cost",
        "energy_mode": "base",
        "scenario_weights": INITIAL_SCENARIO_WEIGHTS,
        "qaoa_depth": 1,
        "M": spec.qubo.one_hot_penalty,
        "phase_offset": spec.phase_offset,
        "phase_scale": spec.phase_scale,
        "qprog_path": str(qprog_path.resolve()),
        "metrics": _metrics_payload(metrics),
    }
    manifest_path = circuit_dir / "uniform_cost_p1.synthesis.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(qprog_path.resolve())
    print(manifest_path.resolve())
    print(json.dumps(manifest["metrics"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
