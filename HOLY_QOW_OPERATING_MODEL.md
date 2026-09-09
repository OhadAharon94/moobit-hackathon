# Holy Qow operating model

Holy Qow is a **network-planning and incident-response optimizer**. It recommends
resilient routing configurations after meaningful topology or demand changes; it
is not positioned as a millisecond packet-forwarding system.

## Selective quantum escalation

1. Network telemetry or an operator identifies congestion, a link failure, or a
   material demand shift.
2. A classical solver produces the first candidate and confidence/quality checks.
3. `SelectiveHybridSolver` checks joint feasibility and the configured
   `maximum_classical_worst_regret`. If the result passes, it returns without
   invoking quantum computation.
4. For difficult or ambiguous cases, Holy Qow runs the QAOA inner solver and the
   adaptive scenario-weight loop.
5. The shared classical evaluator rejects structurally invalid or
   capacity-infeasible samples and compares every accepted route with the
   classical candidate.
6. An SDN controller receives a recommendation only after whole-network safety
   validation and operator-policy checks.

This makes quantum computation an escalation path rather than a continuously
running operational dependency.

## Regional decomposition for large incidents

For a network larger than the demonstrated circuit:

1. Detect the affected links and demands.
2. Expand that region by a configurable boundary so reroutes can use nearby
   alternatives.
3. Freeze unaffected routes and boundary flows.
4. Generate a small candidate-path subproblem for the affected region.
5. Optimize that subproblem with Holy Qow.
6. Reinsert the candidate into the full topology and validate end-to-end capacity,
   reachability, latency, and policy constraints before deployment.

Independent regions may be optimized in parallel. Overlapping or cascading
regions must be merged or coordinated classically; Holy Qow does not claim that a
single current-generation quantum circuit can optimize a nationwide network.

## Auditability

Each adaptive run records its scenario weights, seed, objective definition,
sample distribution, feasibility rate, chosen route, per-scenario regret, and
best-so-far route. See
`artifacts/tables/holy_qow_adaptive_decision_trace.md` for the current experiment.

## Evidence boundaries

- Executed QAOA evidence reaches 18 logical qubits; 24 qubits is synthesis-only.
- The experiments use a simulator and do not establish QPU latency or fidelity.
- Classical baselines remain stronger on the current small fixtures.
- No quantum-advantage or packet-level real-time claim is made.
