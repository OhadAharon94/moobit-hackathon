"""Collect frozen D=4 and Stage 6A synthesis records into one table."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from qera_scaling.instances import generate_instance


def main() -> None:
    stage6a_root = Path(__file__).resolve().parents[1]
    implementation_root = stage6a_root.parent
    frozen = json.loads(
        (
            implementation_root
            / "artifacts"
            / "circuits"
            / "uniform_cost_p1.synthesis.json"
        ).read_text(encoding="utf-8")
    )
    frozen_ops = frozen["metrics"]["count_ops"]
    rows = [
        {
            "instance_id": "qera-d4-frozen",
            "D": 4,
            "logical_bits": 12,
            "synthesized_qubits": frozen["metrics"]["width"],
            "depth": frozen["metrics"]["depth"],
            "gate_count": sum(frozen_ops.values()),
            "two_qubit_gate_count": int(frozen_ops.get("cx", 0)),
            "synthesis_runtime_seconds": "",
            "synthesis_status": "SUCCESS",
            "warning": "Frozen v1.1 reference; historical runtime was not recorded.",
            "source": "v1.1",
        }
    ]
    circuit_dir = stage6a_root / "artifacts" / "scaling" / "circuits"
    for demand_count in (5, 6, 8):
        instance = generate_instance(demand_count)
        path = circuit_dir / f"{instance.instance_id}-p1.synthesis.json"
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                key: record.get(key)
                for key in (
                    "instance_id",
                    "D",
                    "logical_bits",
                    "synthesized_qubits",
                    "depth",
                    "gate_count",
                    "two_qubit_gate_count",
                    "synthesis_runtime_seconds",
                    "synthesis_status",
                    "warning",
                )
            }
            | {"source": "stage6a"}
        )
    output = (
        stage6a_root
        / "artifacts"
        / "scaling"
        / "tables"
        / "scaling_synthesis.csv"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(output.resolve())


if __name__ == "__main__":
    main()
