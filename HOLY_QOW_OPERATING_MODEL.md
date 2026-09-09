# Holy Qow proposed operating model

Holy Qow is an experimental **network-planning and incident-response optimizer**.
It studies resilient routing configurations after meaningful demand or capacity
changes; it is not positioned as a millisecond packet-forwarding system. The
orchestration below is a guarded prototype, not a demonstrated production path.

## Selective quantum escalation

1. Network telemetry or an operator identifies congestion, capacity degradation,
   or a material demand shift.
2. A classical solver produces the first candidate and quality checks.
3. `SelectiveHybridSolver` checks joint feasibility and the configured
   `maximum_classical_worst_regret`. If the result passes, it returns without
   invoking quantum computation.
4. For a difficult case, the wrapper may ask a configured QAOA inner solver for a
   second candidate. Adaptive scenario reweighting is not enabled by this wrapper.
5. The shared classical evaluator rejects structurally invalid or
   capacity-infeasible output. A valid classical candidate is retained unless the
   quantum candidate has strictly better `(worst regret, weighted objective)`
   quality; exact quality ties stay classical.
6. Any future SDN integration would require separate whole-network safety
   validation and operator-policy checks before deployment.

This makes quantum computation an optional escalation path rather than a
continuously running dependency. Current experiments did not establish a
route-quality advantage over the appropriate classical/valid-route baselines, so
the wrapper is an auditable safety mechanism, not evidence for enabling quantum
execution in production.

## Proposed regional decomposition for large incidents

For a network larger than the demonstrated circuit, a future implementation could:

1. Detect the affected links and demands.
2. Expand that region by a configurable boundary so reroutes can use nearby
   alternatives.
3. Freeze unaffected routes and boundary flows.
4. Generate a small candidate-path subproblem for the affected region.
5. Optimize that subproblem with Holy Qow.
6. Reinsert the candidate into the full topology and validate end-to-end capacity,
   reachability, latency, and policy constraints before deployment.

This decomposition has not been implemented or benchmarked here. Independent
regions might be optimized in parallel; overlapping or cascading regions would
need classical coordination. Holy Qow does not claim that a single
current-generation quantum circuit can optimize a nationwide network.

## Auditability

The saved adaptive run records its scenario weights, seed, objective definition,
sample distribution, feasibility rate, chosen route, per-scenario regret, and
best-so-far route. See
`artifacts/tables/holy_qow_adaptive_decision_trace.md` for the in-training trace.
The later held-out and evolution-ablation evidence remains authoritative for
generalization claims.

## Evidence boundaries

- Executed QAOA evidence reaches 18 logical qubits; 24 qubits is synthesis-only.
- The constraint-preserving mixer was executed only at D=4 and did not establish
  a reproducible p=1 route-quality advantage over uniform-valid sampling.
- The experiments use a simulator and do not establish QPU latency or fidelity.
- Classical baselines remain stronger on the current small fixtures.
- No quantum-advantage or packet-level real-time claim is made.
