"""Generate exhaustive Stage 2 QUBO/Ising/alignment evidence."""

from __future__ import annotations

from pathlib import Path

from qera.config import PLAN_VERSION, SCHEMA_VERSION
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator, all_assignments
from qera.exact import exact_adaptive_run
from qera.qubo import (
    all_bitstates,
    bits_from_assignment,
    evaluate_ising,
    evaluate_qubo,
    qubo_to_ising,
)
from qera.records import write_json


def main() -> None:
    evaluator = Evaluator()
    runs = []
    for mode in ("cost", "regret"):
        for record in exact_adaptive_run(evaluator, mode):
            base = build_energy_spec(evaluator, record.weights, mode, "base")
            aligned = build_energy_spec(evaluator, record.weights, mode, "aligned")
            ising = qubo_to_ising(base.qubo)
            runs.append(
                {
                    "objective_mode": mode,
                    "iteration": record.iteration,
                    "weights": record.weights,
                    "M": base.qubo.one_hot_penalty,
                    "Lambda": aligned.capacity_penalty,
                    "qubo_pair_count": len(base.qubo.quadratic),
                    "invalid_ground_gap": base.qubo.verification_summary[
                        "invalid_ground_gap"
                    ],
                    "capacity_gap": aligned.verification_summary["capacity_gap"],
                    "base_ground_assignments": base.verification_summary[
                        "ground_assignments"
                    ],
                    "aligned_ground_assignments": aligned.verification_summary[
                        "ground_assignments"
                    ],
                    "all_aligned_ground_states_joint_feasible": aligned.verification_summary[
                        "all_ground_states_joint_feasible"
                    ],
                    "maximum_valid_qubo_error": max(
                        abs(
                            evaluate_qubo(base.qubo, bits_from_assignment(assignment))
                            - evaluator.weighted_objective(
                                assignment, record.weights, mode
                            )
                        )
                        for assignment in all_assignments()
                    ),
                    "maximum_ising_error": max(
                        abs(
                            evaluate_qubo(base.qubo, bits)
                            - evaluate_ising(ising, bits)
                        )
                        for bits in all_bitstates()
                    ),
                    "base_phase_offset": base.phase_offset,
                    "base_phase_scale": base.phase_scale,
                    "aligned_phase_offset": aligned.phase_offset,
                    "aligned_phase_scale": aligned.phase_scale,
                }
            )
    output = write_json(
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "tables"
        / "encoding_proof.json",
        {
            "schema_version": SCHEMA_VERSION,
            "plan_version": PLAN_VERSION,
            "states_checked_per_run": 4096,
            "valid_assignments_checked_per_run": 81,
            "implementation_findings": [
                "The uniform-cost unrestricted ground set is a symmetric two-way capacity-infeasible tie; the frozen plan names one representative."
            ],
            "runs": runs,
        },
    )
    print(output)


if __name__ == "__main__":
    main()
