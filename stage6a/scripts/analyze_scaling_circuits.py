"""Re-read synthesized qprogs and verify their recorded resource metrics."""

from __future__ import annotations

import json
from pathlib import Path

from classiq import get_transpiled_circuit_metrics
from classiq.interface.generator.quantum_program import QuantumProgram

from qera_scaling.instances import core_instances
from qera_scaling.provenance import sha256_file

TWO_QUBIT_GATES = {
    "cx",
    "cy",
    "cz",
    "swap",
    "rxx",
    "ryy",
    "rzz",
    "rzx",
    "ecr",
    "crx",
    "cry",
    "crz",
    "csx",
    "cu",
    "cp",
    "ch",
}


def main() -> None:
    stage6a_root = Path(__file__).resolve().parents[1]
    implementation_root = stage6a_root.parent
    records = []
    for instance in core_instances():
        if instance.demand_count == 4:
            qprog_path = implementation_root / "artifacts" / "circuits" / "uniform_cost_p1.qprog"
            manifest_path = implementation_root / "artifacts" / "circuits" / "uniform_cost_p1.synthesis.json"
        else:
            stem = f"{instance.instance_id}-p1"
            qprog_path = stage6a_root / "artifacts" / "scaling" / "circuits" / f"{stem}.qprog"
            manifest_path = stage6a_root / "artifacts" / "scaling" / "circuits" / f"{stem}.synthesis.json"
        qprog = QuantumProgram.model_validate_json(qprog_path.read_text(encoding="utf-8"))
        metrics = get_transpiled_circuit_metrics(qprog)
        operations = {str(key): int(value) for key, value in metrics.count_ops.items()}
        total_gates = sum(operations.values())
        two_qubit_gates = sum(
            count for gate, count in operations.items() if gate.lower() in TWO_QUBIT_GATES
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if instance.demand_count == 4:
            expected = manifest["metrics"]
            expected_width = expected["width"]
            expected_depth = expected["depth"]
            expected_operations = expected["count_ops"]
        else:
            expected_width = manifest["synthesized_qubits"]
            expected_depth = manifest["depth"]
            expected_operations = manifest["count_ops"]
        if (
            metrics.width != expected_width
            or metrics.depth != expected_depth
            or operations != expected_operations
        ):
            raise ValueError(f"saved resource metrics drifted for {instance.instance_id}")
        records.append(
            {
                "instance_id": instance.instance_id,
                "D": instance.demand_count,
                "width": metrics.width,
                "depth": metrics.depth,
                "total_gates": total_gates,
                "two_qubit_gates": two_qubit_gates,
                "two_qubit_fraction": two_qubit_gates / total_gates,
                "count_ops": operations,
                "qprog_sha256": sha256_file(qprog_path),
                "manifest_sha256": sha256_file(manifest_path),
                "execution_scope": (
                    "simulator-executed" if instance.demand_count <= 6 else "synthesis-only"
                ),
                "hardware_interpretation": (
                    "Hardware-agnostic synthesis; high two-qubit fraction makes physical-device fidelity uncertain."
                ),
            }
        )
    output = (
        stage6a_root
        / "artifacts"
        / "scaling"
        / "tables"
        / "scaling_circuit_analysis.json"
    )
    output.write_text(
        json.dumps({"circuits": records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output.resolve())
    print(json.dumps({"circuits": records}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
