"""Write the versioned Stage 6A findings document from saved tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _pct(value: float, digits: int = 3) -> str:
    return f"{100.0 * value:.{digits}f}%"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    tables = root / "artifacts" / "scaling" / "tables"
    synthesis = pd.read_csv(tables / "scaling_synthesis.csv").set_index("D")
    qubo = pd.read_csv(tables / "scaling_qubo.csv").set_index("D")
    classical = pd.read_csv(tables / "scaling_classical.csv").set_index("D")
    qaoa = pd.read_csv(tables / "scaling_qaoa.csv")

    def sample(D: int, method: str) -> pd.Series:
        return qaoa[(qaoa["D"] == D) & (qaoa["method"] == method)].iloc[0]

    d5q, d5b = sample(5, "qaoa"), sample(5, "uniform_random_bitstrings")
    d6q, d6b = sample(6, "qaoa"), sample(6, "uniform_random_bitstrings")
    lines = [
        "# Q-ERA Stage 6A — Scalability Findings",
        "",
        "**Status:** complete core scalability study; v1.1 remains frozen.",
        "",
        "## Outcome",
        "",
        "Stage 6A produced deterministic D=4, 5, 6, and 8 routing instances, exact and heuristic classical benchmarks, verified QUBOs, four Classiq synthesis points, and real p=1 QAOA sample distributions for D=5 and D=6. The evidence supports a measured scaling story, not a quantum-advantage claim.",
        "",
        "## Measured resource scaling",
        "",
        "| D | Logical/synthesized qubits | Depth | Total gates | Two-qubit gates | QUBO couplings | Coupling density |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for D in (4, 5, 6, 8):
        lines.append(
            f"| {D} | {int(synthesis.loc[D, 'logical_bits'])}/{int(synthesis.loc[D, 'synthesized_qubits'])} | "
            f"{int(synthesis.loc[D, 'depth'])} | {int(synthesis.loc[D, 'gate_count'])} | "
            f"{int(synthesis.loc[D, 'two_qubit_gate_count'])} | {int(qubo.loc[D, 'nonzero_quadratic'])} | "
            f"{qubo.loc[D, 'quadratic_density']:.3f} |"
        )
    lines += [
        "",
        "For fixed K=3, logical width follows 3D exactly. The synthesized circuits used no ancilla overhead in this series. Width therefore grew linearly, while depth and two-qubit gates grew faster and non-monotonically with the generated interaction pattern. The quadratic coupling density stayed near 0.51–0.52, so these instances did not become sparse as D increased.",
        "",
        "The two-qubit-gate fraction is high (roughly 53–58%). These are hardware-agnostic synthesis results; they establish resource growth and simulator feasibility, not expected physical-device fidelity.",
        "",
        "## Quantum sampling results",
        "",
        "| D | Method | One-hot mass | Joint-feasible mass | Best feasible objective gap | Near-optimal mass (absolute gap ≤0.01) |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for D in (4, 5, 6):
        for method, label in (
            ("qaoa", "QAOA p=1"),
            ("uniform_random_bitstrings", "Random bitstrings"),
            ("uniform_random_valid_routes", "Random valid routes"),
        ):
            row = sample(D, method)
            lines.append(
                f"| {D} | {label} | {_pct(row['one_hot_probability'])} | "
                f"{_pct(row['joint_feasible_probability'])} | "
                f"{100.0 * row['selected_relative_gap']:.2f}% | "
                f"{_pct(row['near_optimal_joint_probability_gap_0_01'])} |"
            )
    d5_feasible = round(d5q["joint_feasible_probability"] * d5q["total_shots"])
    d6_feasible = round(d6q["joint_feasible_probability"] * d6q["total_shots"])
    lines += [
        "",
        f"At D=5, QAOA produced {d5_feasible} jointly feasible shots out of 4,096, the same feasible count as this seeded random-bit control. Its best feasible route was {100*d5q['selected_relative_gap']:.2f}% above exact, versus {100*d5b['selected_relative_gap']:.2f}% for random bits, and it reached the exact minimax-regret value among its samples.",
        "",
        f"At D=6, QAOA again produced {d6_feasible} jointly feasible shots. Its one-hot mass was {_pct(d6q['one_hot_probability'])}, versus {_pct(d6b['one_hot_probability'])} for random bits, and its joint-feasible mass was {_pct(d6q['joint_feasible_probability'])}, versus {_pct(d6b['joint_feasible_probability'])}. The best feasible objective gap was {100*d6q['selected_relative_gap']:.2f}% for QAOA and {100*d6b['selected_relative_gap']:.2f}% for random bits.",
        "",
        "These D=6 comparisons are encouraging but based on one optimizer seed and small feasible counts. They demonstrate measurable concentration in this run, not statistical superiority. Neither larger QAOA run sampled the exact weighted optimum.",
        "",
        "The random-valid-route control remains the strongest practical baseline: it allocates all shots to the one-hot subspace and recovered the exact optimum at every executed size. This isolates the principal limitation of the current |+> initialization plus transverse-X mixer: useful one-hot volume shrinks theoretically as (3/8)^D.",
        "",
        "## Classical comparison",
        "",
        f"Exact enumeration remained inexpensive through D=8 (3^8 = 6,561 valid routes; recorded runtime {classical.loc[8, 'exact_runtime_seconds']:.3f} s). Simulated annealing and the 4,096-shot random-valid control also recovered the exact weighted optimum throughout the core grid. Consequently, this experiment shows no computational quantum advantage and is not yet a hard classical benchmark.",
        "",
        "## Interpretation for the hackathon",
        "",
        "The study strengthens the submission by connecting the validated Q-ERA formulation to measured quantum resource growth and by exposing a concrete quantum-design bottleneck rather than hiding it. Robust scenarios alter Hamiltonian coefficients without adding route-register qubits, while candidate-path count and demand count control width. Evolution remains in the adaptive scenario-weight loop validated in v1.1; Stage 6A intentionally tests the static inner solve first.",
        "",
        "The next algorithmic research direction is a one-hot-preserving state preparation and mixer. That would remove the exponentially shrinking invalid part of the binary Hilbert space. It is explicitly outside Stage 6A and must not be presented as implemented evidence.",
        "",
        "## Evidence boundaries",
        "",
        "- D=8 is synthesis-only; no 24-qubit statevector QAOA execution was attempted.",
        "- Simulator runtimes are classical-emulation measurements, not QPU speed estimates.",
        "- Synthesis was hardware-agnostic; no backend-specific fidelity or cost comparison was performed.",
        "- Quantum sampling results use one seed and 4,096 final shots per method.",
        "- All plots are generated from the saved CSV records in `artifacts/scaling/tables/`.",
        "",
        "## Figures",
        "",
        "1. `artifacts/scaling/figures/01_quantum_width.png`",
        "2. `artifacts/scaling/figures/02_circuit_resources.png`",
        "3. `artifacts/scaling/figures/03_qubo_interactions.png`",
        "4. `artifacts/scaling/figures/04_feasible_probability.png`",
        "5. `artifacts/scaling/figures/05_solution_quality.png`",
        "",
    ]
    output = root / "SCALABILITY_FINDINGS.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()
