"""Analyze existing D=4 X-mixer and constrained-mixer qprogs only."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from classiq import get_transpiled_circuit_metrics
from classiq.interface.generator.quantum_program import QuantumProgram
import pandas as pd

from qera_stage6b.provenance import sha256_file


TWO_QUBIT_GATES = {
    "cx",
    "cy",
    "cz",
    "ch",
    "crx",
    "cry",
    "crz",
    "cphase",
    "cp",
    "cu",
    "csx",
    "ecr",
    "rxx",
    "ryy",
    "rzz",
    "rzx",
    "swap",
}


def _metrics(path: Path) -> dict:
    qprog = QuantumProgram.model_validate_json(path.read_text(encoding="utf-8"))
    metrics = get_transpiled_circuit_metrics(qprog)
    count_ops = dict(metrics.count_ops)
    total = sum(int(count) for count in count_ops.values())
    two_qubit = sum(
        int(count)
        for name, count in count_ops.items()
        if name.lower() in TWO_QUBIT_GATES
    )
    return {
        "width": int(metrics.width),
        "depth": int(metrics.depth),
        "gate_count": total,
        "two_qubit_gate_count": two_qubit,
        "two_qubit_gate_fraction": two_qubit / total,
        "count_ops": count_ops,
        "qprog_sha256": sha256_file(path),
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts" / "stage6b"
    table_path = artifacts / "tables" / "circuit_resource_comparison.csv"
    report_path = artifacts / "tables" / "circuit_resource_analysis.json"
    if table_path.exists() or report_path.exists():
        raise FileExistsError("refusing to overwrite Stage 6B circuit analysis")

    x_path = root / "artifacts" / "circuits" / "uniform_cost_p1.qprog"
    constrained_path = artifacts / "d4" / "constrained_p1.qprog"
    constrained_manifest = json.loads(
        (artifacts / "d4" / "constrained_p1.synthesis.json").read_text(
            encoding="utf-8"
        )
    )
    x = _metrics(x_path)
    constrained = _metrics(constrained_path)
    execution_runtimes = []
    for manifest_path in sorted((artifacts / "d4" / "runs").glob("seed-*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["status"] == "RAW_SAMPLE_SAVED":
            execution_runtimes.append(float(manifest["execution_runtime_seconds"]))
    rows = [
        {
            "D": 4,
            "p": 1,
            "mixer": "transverse_x_frozen",
            **{key: value for key, value in x.items() if key != "count_ops"},
            "synthesis_runtime_seconds": None,
            "optimizer_runtime_seconds_mean": None,
            "optimizer_runtime_seconds_min": None,
            "optimizer_runtime_seconds_max": None,
            "runtime_note": "Historical synthesis and optimizer runtimes were not recorded.",
        },
        {
            "D": 4,
            "p": 1,
            "mixer": "constraint_preserving_xy",
            **{
                key: value
                for key, value in constrained.items()
                if key != "count_ops"
            },
            "synthesis_runtime_seconds": constrained_manifest[
                "synthesis_runtime_seconds"
            ],
            "optimizer_runtime_seconds_mean": sum(execution_runtimes)
            / len(execution_runtimes),
            "optimizer_runtime_seconds_min": min(execution_runtimes),
            "optimizer_runtime_seconds_max": max(execution_runtimes),
            "runtime_note": "Three independent Stage 6B seeds.",
        },
    ]
    table_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(table_path, index=False)

    overhead = {}
    for metric in ("width", "depth", "gate_count", "two_qubit_gate_count"):
        baseline = float(x[metric])
        candidate = float(constrained[metric])
        overhead[metric] = {
            "x_mixer": x[metric],
            "constrained_mixer": constrained[metric],
            "absolute_change": candidate - baseline,
            "relative_change": (candidate - baseline) / baseline,
            "ratio": candidate / baseline,
        }
    report = {
        "schema_version": "stage6b-1.0",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "comparison_scope": "same frozen D=4 uniform-cost objective and p=1",
        "x_mixer": x,
        "constraint_preserving_xy": constrained,
        "overhead": overhead,
        "synthesis_runtime_seconds": {
            "x_mixer": None,
            "constraint_preserving_xy": constrained_manifest[
                "synthesis_runtime_seconds"
            ],
            "note": "The frozen X-mixer artifact did not record synthesis runtime.",
        },
        "optimizer_runtime_seconds": {
            "x_mixer": None,
            "constraint_preserving_xy_mean": sum(execution_runtimes)
            / len(execution_runtimes),
            "constraint_preserving_xy_min": min(execution_runtimes),
            "constraint_preserving_xy_max": max(execution_runtimes),
            "note": "The frozen X-mixer artifact did not record optimizer runtime.",
        },
        "engineering_interpretation": {
            "simulator_feasible": True,
            "nisq_assessment": "marginal",
            "limiting_factor": "164 two-qubit gates and synthesized depth 101",
            "hardware_scope": (
                "Hardware-agnostic synthesis only; no backend-specific fidelity or "
                "execution-cost claim is made."
            ),
        },
        "table_path": str(table_path.resolve()),
        "table_sha256": sha256_file(table_path),
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(report_path.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
