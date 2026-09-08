# Q-ERA Stage 6A — Scalability Findings

**Status:** complete core scalability study; v1.1 remains frozen.

## Outcome

Stage 6A produced deterministic D=4, 5, 6, and 8 routing instances, exact and heuristic classical benchmarks, verified QUBOs, four Classiq synthesis points, and real p=1 QAOA sample distributions for D=5 and D=6. The evidence supports a measured scaling story, not a quantum-advantage claim.

## Measured resource scaling

| D | Logical/synthesized qubits | Depth | Total gates | Two-qubit gates | QUBO couplings | Coupling density |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 12/12 | 65 | 154 | 84 | 34 | 0.515 |
| 5 | 15/15 | 79 | 236 | 136 | 55 | 0.524 |
| 6 | 18/18 | 138 | 294 | 160 | 80 | 0.523 |
| 8 | 24/24 | 246 | 492 | 280 | 140 | 0.507 |

For fixed K=3, logical width follows 3D exactly. The synthesized circuits used no ancilla overhead in this series. Width therefore grew linearly, while depth and two-qubit gates grew faster and non-monotonically with the generated interaction pattern. The quadratic coupling density stayed near 0.51–0.52, so these instances did not become sparse as D increased.

The two-qubit-gate fraction is high (roughly 53–58%). These are hardware-agnostic synthesis results; they establish resource growth and simulator feasibility, not expected physical-device fidelity.

## Quantum sampling results

| D | Method | One-hot mass | Joint-feasible mass | Best feasible objective gap | Near-optimal mass (absolute gap ≤0.01) |
|---:|---|---:|---:|---:|---:|
| 4 | QAOA p=1 | 5.225% | 2.344% | 0.00% | 0.049% |
| 4 | Random bitstrings | 2.197% | 1.050% | 5.26% | 0.000% |
| 4 | Random valid routes | 100.000% | 47.266% | 0.00% | 1.343% |
| 5 | QAOA p=1 | 0.586% | 0.195% | 0.40% | 0.024% |
| 5 | Random bitstrings | 0.757% | 0.195% | 14.55% | 0.000% |
| 5 | Random valid routes | 100.000% | 29.712% | 0.00% | 1.562% |
| 6 | QAOA p=1 | 0.610% | 0.195% | 3.23% | 0.024% |
| 6 | Random bitstrings | 0.244% | 0.049% | 6.20% | 0.000% |
| 6 | Random valid routes | 100.000% | 26.221% | 0.00% | 1.685% |

At D=5, QAOA produced 8 jointly feasible shots out of 4,096, the same feasible count as this seeded random-bit control. Its best feasible route was 0.40% above exact, versus 14.55% for random bits, and it reached the exact minimax-regret value among its samples.

At D=6, QAOA again produced 8 jointly feasible shots. Its one-hot mass was 0.610%, versus 0.244% for random bits, and its joint-feasible mass was 0.195%, versus 0.049%. The best feasible objective gap was 3.23% for QAOA and 6.20% for random bits.

These D=6 comparisons are encouraging but based on one optimizer seed and small feasible counts. They demonstrate measurable concentration in this run, not statistical superiority. Neither larger QAOA run sampled the exact weighted optimum.

The random-valid-route control remains the strongest practical baseline: it allocates all shots to the one-hot subspace and recovered the exact optimum at every executed size. This isolates the principal limitation of the current |+> initialization plus transverse-X mixer: useful one-hot volume shrinks theoretically as (3/8)^D.

## Classical comparison

Exact enumeration remained inexpensive through D=8 (3^8 = 6,561 valid routes; recorded runtime 0.930 s). Simulated annealing and the 4,096-shot random-valid control also recovered the exact weighted optimum throughout the core grid. Consequently, this experiment shows no computational quantum advantage and is not yet a hard classical benchmark.

## Interpretation for the hackathon

The study strengthens the submission by connecting the validated Q-ERA formulation to measured quantum resource growth and by exposing a concrete quantum-design bottleneck rather than hiding it. Robust scenarios alter Hamiltonian coefficients without adding route-register qubits, while candidate-path count and demand count control width. Evolution remains in the adaptive scenario-weight loop validated in v1.1; Stage 6A intentionally tests the static inner solve first.

The next algorithmic research direction is a one-hot-preserving state preparation and mixer. That would remove the exponentially shrinking invalid part of the binary Hilbert space. It is explicitly outside Stage 6A and must not be presented as implemented evidence.

## Evidence boundaries

- D=8 is synthesis-only; no 24-qubit statevector QAOA execution was attempted.
- Simulator runtimes are classical-emulation measurements, not QPU speed estimates.
- Synthesis was hardware-agnostic; no backend-specific fidelity or cost comparison was performed.
- Quantum sampling results use one seed and 4,096 final shots per method.
- All plots are generated from the saved CSV records in `artifacts/scaling/tables/`.

## Figures

1. `artifacts/scaling/figures/01_quantum_width.png`
2. `artifacts/scaling/figures/02_circuit_resources.png`
3. `artifacts/scaling/figures/03_qubo_interactions.png`
4. `artifacts/scaling/figures/04_feasible_probability.png`
5. `artifacts/scaling/figures/05_solution_quality.png`
