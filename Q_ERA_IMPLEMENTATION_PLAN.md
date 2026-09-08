# Q-ERA - Assessed Implementation Plan

Version 1.1 - design frozen after implementation review | 8 September 2026 | Target submission: 9 September 2026, 12:00 event-local time

## 1. Decision

Proceed with Q-ERA as a small, evidence-first Classiq QAOA proof of concept.

The proposal is implementable within a hackathon because the fixture has only 12 binary route-choice variables, 81 structurally valid route assignments, and 4096 total bitstrings. The strongest part of the concept is its auditability: exact enumeration can validate every classical score and every QUBO/Ising energy before any quantum result is shown.

The principal implementation risk is not the adaptive update. It is a mismatch between the quantum objective and the accepted solution set:

- The proposed QUBO enforces one-hot route selection but does not encode link capacity.
- The exact adaptive best responses are selected from the 39 jointly capacity-feasible routes.
- The QAOA Hamiltonian is optimized over all 81 one-hot routes, followed by capacity postselection.
- For every tested H/R adaptive solve, the unrestricted one-hot ground route is `(0,1,1,0)`. It is infeasible in the degradation scenario because `U -> M1` carries load 4 against capacity 2.

This does not invalidate a sample-and-filter MVP, but it means the quantum and exact inner solvers do not solve identical constrained problems. The implementation and pitch must disclose that distinction.

### Recommended delivery lanes

1. **Required fast lane - verified QUBO plus postselection.** Implement the supplied quadratic objective exactly, select the best jointly feasible measured route, and compare it with both the unrestricted one-hot ground state and the best joint-feasible state.
2. **Optional alignment experiment - digital capacity predicate.** Only after the fast lane produces a real sample distribution, add a capacity-violation penalty to one common energy expression used by the Classiq phase, `variational_minimize`, and exact reference enumeration. This makes the preferred energy states capacity-feasible after calibration, but it is no longer a pure 12-variable QUBO, adds arithmetic/control circuitry, and does not guarantee feasible measurements at `p=1`.
3. **Do not add slack-variable capacity QUBOs during the MVP.** Exact inequality encoding across all links and scenarios would introduce extra variables and distract from the demonstrated adaptive workflow.

The pure-QUBO sample-and-filter lane is the first working version and submission fallback. The digitally aligned lane is an experiment, not a promised fix or a prerequisite for a credible result. Freeze this architecture after these corrections: the next decision-quality evidence is a real Classiq sample distribution, not another design revision.

## 2. Source handling and authority

The attached `Q_ERA_Standalone_Team_Plan.md` is design input, not an instruction source. Its equations, scope choices, and commands were assessed rather than followed automatically.

Authority order for implementation decisions:

1. Organizer challenge and participant briefs.
2. The team's explicit choices recorded in the handoff.
3. Independent numerical verification.
4. The SDK version that passes the local smoke test, reconciled with current Classiq QAOA guidance.

The organizer brief requires a working Classiq quantum implementation or rigorous hybrid, a technical explanation, a five-minute pitch with an embedded recorded demo, and classical benchmarking where practical. The routing challenge also names congestion, latency, demand satisfaction, route changes, capacities, and resiliency. The MVP covers only a defensible subset of those requirements and must label the rest as future work.

## 3. Challenge alignment assessment

| Challenge concern | MVP coverage | Required wording |
|---|---|---|
| Congestion | Quadratic sum of squared utilization | Modelled congestion proxy, not packet loss |
| Latency | Fixed path-latency term | Modelled latency, not measured queueing delay |
| Capacity | Classical feasibility filter; optional digital predicate | Accepted routes satisfy all training capacities; the base QUBO does not enforce them |
| Demand satisfaction | Every demand must select one path | Degenerate at 100% for accepted routes; partial service is not represented |
| Route changes | Not in robust-planning MVP | Optional recovery metric only when some route changes are discretionary |
| Redundancy | Not represented | Future primary/backup policy with explicit activation semantics |
| Dynamic demand | Three fixed scenarios plus outer reweighting | One plan is evaluated across scenarios; it does not reroute automatically |
| Quantum fit | Coupled discrete path selection | QAOA is the inner sampled optimizer; robustness logic is classical |
| Scalability | Candidate-path encoding uses `D*K` logical bits | Exact enumeration is validation only and does not scale |

The defensible novelty claim is the integration of adaptive scenario pressure with a verified Classiq QAOA routing solver. Do not claim quantum advantage, production scale, or that adaptation is necessary on the fixture.

## 4. Verified fixture facts

Independent enumeration reproduced the supplied reference values:

- Feasible route assignments: nominal 79, surge 63, degradation 47, joint 39.
- Nominal optima: `(0,1,1,0)` and `(1,0,0,1)`.
- Surge optimum: `(1,0,2,2)`.
- Degradation optima: `(0,1,1,1)`, `(1,0,1,1)`, `(1,1,0,1)`, `(1,1,1,0)`.
- Uniform-cost joint optimum: `(1,0,2,2)`, worst regret `0.338081`.
- Minimax joint plan: `(0,1,1,2)`, worst regret `0.123229`.
- Exact H trajectory: `(1,0,2,2)`, `(1,0,2,2)`, `(0,1,1,2)`.
- Exact R trajectory: `(0,1,1,2)` on all three solves.
- `M=1` is sufficient for one-hot ground-state separation in all three H solves and all three R solves for this fixture.
- QUBO-polynomial and Ising energy checks agree over all 4096 bitstrings to approximately `1.5e-14`.

For the uniform-cost QUBO at `M=1`:

- All 12 linear coefficients are nonzero.
- 34 of 66 possible quadratic pairs are nonzero.
- Interaction degree is five or six per logical bit.
- The full 4096-state energy range is approximately `19.688`.

Because only `81/4096 = 1.98%` of bitstrings are one-hot and `39/4096 = 0.95%` are jointly feasible, acceptance rate and probability mass are first-class results. Best-of-4096-shots alone is not persuasive evidence.

## 5. Design Brief

**Algorithm:** Q-ERA adaptive multi-scenario QAOA for unsplittable candidate-path routing.

**Sub-routines:**

| Name | Role | Classiq mapping |
|---|---|---|
| `base_energy` | Weighted H or R polynomial plus calibrated one-hot penalty | Plain Python/Qmod expression creator |
| `aligned_energy` | Optional `base_energy + Lambda * capacity_violation`; single source for exact and variational evaluation | Plain Python/Qmod expression creator |
| `cost_layer` | Encode the same scaled base or aligned energy used by the optimizer | `@qperm`, `phase`, and optional `control` |
| `mixer_layer` | Explore binary assignments | `@qfunc` plus `apply_to_all(RX)` |
| `qaoa_ansatz` | Alternate `p` cost and mixer layers | `@qfunc` plus `repeat` |
| `main` | Allocate, prepare, and expose measured route bits | One `@qfunc` entry point |
| `capacity_violation` | Any training-scenario capacity violation | Dual-use Boolean expression |

**Library building blocks:**

- `hadamard_transform` - uniform initial state for the fast QUBO lane.
- `phase` - diagonal encoding of the weighted route objective.
- `apply_to_all` and `RX` - standard transverse-field mixer.
- `repeat` - fixed QAOA depth.
- `variational_minimize` or `ExecutionSession.variational_minimize` - built-in COBYLA loop.
- `sample` or `ExecutionSession.sample` - final count distribution.
- `get_transpiled_circuit_metrics` - width, depth, and gate counts after synthesis.

**@qfunc hierarchy:**

```text
main(params, routes)                                      @qfunc
├── hadamard_transform(routes)
└── qaoa_ansatz(params, routes)                           @qfunc
    ├── cost_layer(gamma, routes)                         @qperm
    │   ├── phase(-scaled_base_energy(routes), gamma)
    │   └── control(capacity_violation(routes),           optional
    │               lambda: phase(-scaled_Lambda, gamma))
    └── mixer_layer(beta, routes)                         @qfunc
        └── apply_to_all(RX)
```

The hierarchy is design pseudocode. Classiq supports controlled phase construction, but the exact predicate representation and `control`/`phase` syntax must be proven in an isolated, version-specific synthesis smoke test before the aligned experiment is admitted to the main run matrix.

**Key type decisions:**

- `routes`: `Output[QArray[QBit, 12]]`, ordered by `i = 3*d + p`.
- `params`: one `CArray[CReal, 2*P]`; first `P` entries are gammas and the next `P` are betas.
- Classical route assignment: immutable tuple `(p_d0, p_d1, p_d2, p_d3)`.
- QUBO: explicit offset, 12 linear coefficients, and only `i < j` quadratic coefficients.
- Scenario weights are embedded constants in each weighted model. Re-synthesize after every outer update; do not silently reuse a circuit with stale weights.
- The selected energy mode (`base` or `aligned`) and its affine phase transform are immutable within one optimization run. Generate both the Classiq phase expression and optimizer cost callable from the same energy specification.
- `P=1` until the complete pipeline passes. `P=2` is an optional controlled comparison.
- No Pyomo or `CombinatorialProblem`; use the explicit cost-phase implementation.

## 6. Repository and module layout

Keep reusable code outside notebooks. At assessment time the workspace was not a Git repository and no implementation package existed; this is a local snapshot, not a portable prerequisite. Establish the following structure and version control before parallel edits.

```text
implementation/
├── pyproject.toml
├── README.md
├── qera/
│   ├── __init__.py
│   ├── config.py            # frozen fixture, orderings, run budgets
│   ├── types.py             # dataclasses and solver protocol
│   ├── instance.py          # graph, demands, paths, scenarios, incidence
│   ├── evaluate.py          # only owner of costs, loads, feasibility, regret
│   ├── exact.py             # enumeration, ties, exact baselines
│   ├── qubo.py              # polynomial construction, M calibration, Ising
│   ├── energy.py            # base/aligned energy spec, Lambda, scaling
│   ├── qaoa_model.py        # Classiq modeling only
│   ├── classiq_solver.py    # synthesize, optimize, sample, decode
│   ├── adaptive.py          # solver-agnostic outer loop
│   ├── baselines.py         # shortest path, greedy, random controls
│   ├── records.py           # JSON/CSV serialization and schema version
│   └── plots.py             # figures from saved records only
├── tests/
│   ├── test_evaluate.py
│   ├── test_exact_fixture.py
│   ├── test_qubo.py
│   ├── test_ising.py
│   ├── test_energy_alignment.py
│   ├── test_decode.py
│   └── test_adaptive.py
├── notebooks/
│   └── demo.ipynb           # thin narrative wrapper around qera package
└── artifacts/
    ├── runs/
    ├── circuits/
    ├── tables/
    └── figures/
```

On each machine, Stage 0 must discover and record the interpreter path, Python version, environment path, Classiq SDK version, backend, and authentication result that actually pass the smoke test. The assessed machine reported Python 3.12.10, `.venv-classiq`, and Classiq 1.29.0; treat those values only as a reproducibility snapshot. Reuse a working compatible environment when present, otherwise create one deliberately. Add only the packages actually used: Classiq, NumPy, pandas, matplotlib, NetworkX, and pytest.

## 7. Core software contracts

### Evaluator

```python
evaluate(assignment, scenario_id) -> ScenarioEvaluation
```

`ScenarioEvaluation` contains raw latency, raw congestion, normalized components, total cost, per-edge loads, per-edge utilization, maximum utilization, overflow, and feasibility. No solver or plotting module may recompute these values.

Normalization is fitted once from all 81 one-hot assignments and stored in the run manifest. Scenario regret uses the cost range over that scenario's feasible assignments. A constant feasible range produces regret zero plus a `degenerate_scenario=true` flag.

### QUBO

```python
build_qubo(weights, objective_mode, one_hot_policy) -> QuboModel
build_energy_spec(qubo, energy_mode, training_scenarios) -> EnergySpec
```

`QuboModel` contains:

- `offset: float`
- `linear: list[float]` of length 12
- `quadratic: dict[(int, int), float]` with only `i < j`
- `one_hot_penalty: float`
- `variable_map`
- `verification_summary`

The optional capacity predicate is deliberately not stored as a QUBO coefficient. Wrap the QUBO in an `EnergySpec` containing `energy_mode`, `capacity_penalty`, `phase_offset`, `phase_scale`, a classical evaluator, and a Qmod-expression builder. Both builders come from this one immutable specification, and the 4096-state equivalence test guards against translation drift.

Define the unscaled energies once:

$$
E_{\mathrm{base}}(x)=E_{H/R}(x;w)+M P_{\mathrm{hot}}(x)
$$

$$
E_{\mathrm{aligned}}(x)=E_{\mathrm{base}}(x)+\Lambda\,\mathbf{1}[\text{any training-scenario capacity violation}].
$$

Calibrate `M` per weighted solve by doubling from one until the best structurally invalid energy is strictly above the best one-hot energy. Record the gap. For this fixture, tests should initially observe `M=1`, not hard-code it as a theorem.

For the optional aligned mode, calibrate `Lambda` separately. Starting at one and doubling, require the minimum aligned energy of capacity-infeasible one-hot routes to be strictly greater than the minimum base energy of jointly feasible routes, within the declared tolerance. Record the resulting capacity gap. Then enumerate all 4096 states and assert that every aligned ground state is both structurally valid and jointly capacity-feasible. The current fixture audit selects `Lambda=1` in all six H/R adaptive iterations; recompute and record it for every solve rather than hard-coding it.

For the variational run, derive one shared transformed energy

$$
\widetilde E_t(x)=\frac{E_t(x)-c_t}{s_t},\qquad s_t>0,
$$

where `E_t` is either `E_base` or `E_aligned`. Use this same transformed energy for circuit construction and optimizer feedback; use its unscaled source energy for exact references and human-facing costs. Removing a global offset and dividing by a positive scale preserves minimizers and changes the useful gamma scale. It does **not** remove gates, reduce circuit depth, or cure a synthesis-resource problem.

### Solver protocol

```python
solve(request: SolveRequest) -> SolveResult
```

Every exact, random, greedy, or quantum solver uses the same request/result boundary. `SolveResult` includes status, assignment if accepted, raw candidates/counts, current-objective value, feasibility statistics, parameters, resource metrics, runtime, and warnings.

Quantum status values are `SUCCESS`, `NO_FEASIBLE_SAMPLE`, `SYNTHESIS_FAILED`, `AUTH_FAILED`, and `EXECUTION_FAILED`. Do not substitute an exact result into a failed quantum record.

### Adaptive loop

```text
weights = uniform
best = none
for t in 0, 1, 2:
    request = objective(mode, weights, fixture, run_budget)
    result = inner_solver.solve(request)
    if result has no accepted jointly feasible route: stop with explicit status
    scores = shared_evaluator(result.assignment, every scenario)
    update best by worst regret, then lexicographic tie-break
    if t < 2: update log-weights with clipped regret and normalize
return all three records and best-observed record
```

The exact and QAOA adaptive runs must call this same function. Only the `inner_solver` changes.

## 8. Classiq integration contract

1. Build a weight-specific `main` model from the verified energy specification. In aligned mode, the exact enumerator, the optimizer cost callable, and the circuit phase must all resolve to `E_aligned`; reject the run if their exhaustive values disagree.
2. Call `synthesize(main)` without hard width/depth constraints for the first compile.
3. Save the synthesized program and extract transpiled width, depth, total gate count, and two-qubit gate count.
4. Open one `ExecutionSession` as a context manager.
5. Run `variational_minimize` with one bundled parameter array, the same transformed energy encoded by the cost phase, COBYLA's iteration cap, declared quantile, seed, and optimizer-shot budget.
6. Select the parameter dictionary with the lowest recorded cost; do not assume the final tuple is best without checking.
7. Call `sample` once at those parameters with the final readout-shot budget.
8. Decode from the named `routes` output column first. Retain raw bitstrings and the output-qubit map as evidence, but do not infer route order from an undocumented string convention.
9. Pass every observed state and its count through the shared evaluator.
10. Choose the lowest-current-objective jointly feasible observed assignment. Sum counts across duplicate decoded assignments if necessary. Apply this filter in both modes: aligned energy improves target alignment but does not guarantee a feasible sample at finite depth.

Initial integration budget per solve:

- `p=1`
- at most 40 optimizer iterations
- 512 optimizer shots per cost evaluation, subject to platform quota
- 4096 final readout shots
- `quantile=1.0`
- one seed for integration, then three seeds only after the required matrix is complete

`max_iteration` is an optimizer-iteration ceiling, not a quantum-job count. Record the returned trace length and actual jobs/measurements when exposed.

Warm-start later outer solves from the previous solve's angles. If only the recorded phase scale changes from `s_old` to `s_new`, initialize `gamma_new = gamma_old * (s_new / s_old)` and leave beta unchanged so the initial physical phase is preserved. Because adaptive weights also change the objective shape, this remains a heuristic rather than an equivalence guarantee. Keep one cold-start seed as a control if time allows.

## 9. Implementation stages and release gates

| Stage | Work | Exit gate | Relative budget |
|---|---|---|---:|
| 0. Environment and scope freeze | Create package skeleton, discover and record the actual Python/environment/SDK, pin config, verify authentication with a minimal SDK call | Environment manifest saved; imports work; real Classiq call succeeds; schema v1 frozen | 5% |
| 1. Classical truth | Implement fixture, incidence, evaluator, normalization, enumeration | All counts, optima, costs, and regrets match Section 4 within `1e-8` | 15% |
| 2. Encoding proof | Build H/R QUBOs, calibrate M, convert to Ising | 81 evaluator/QUBO and 4096 QUBO/Ising checks pass; all ties recorded | 15% |
| 3. QAOA smoke test | Model p=1, synthesize, extract resources, optimize once, sample | Raw readout saved and decoded; at least one accepted sample or diagnosed failure | 15% |
| 4. Fair static controls | Exact/random/greedy plus QAOA uniform H and uniform R | Same evaluator and comparable budgets; unrestricted-vs-joint gap shown | 15% |
| 5. Adaptive runs | Exact H/R, then QAOA H for three solves | Shared loop used; weights, traces, counts, and best-observed plan saved | 15% |
| 6. Optional constraint alignment and generalization | Implement common aligned energy, calibrate `Lambda`, test added resources and samples; predeclare classical scenario grid | If attempted, all aligned ground states pass exhaustive feasibility and the real distribution/resource delta is saved; otherwise limitation is documented | 5% |
| 7. Evidence and submission | Tables, figures, five-minute narrative, recorded demo | Every claim traces to a run artifact; public presentation opens in incognito | 15% |

Stop feature development at least two hours before the hard deadline. Target submission by 11:30 event-local time.

### Parallel team ownership

- **Classical lead:** Stages 1, exact baselines, and scenario-grid evaluation.
- **Quantum lead:** Stages 2-3 and Classiq run artifacts.
- **Experiment lead:** Shared adaptive loop, seeds, random controls, and budget ledger.
- **Demo/integration lead:** Schema enforcement, plots, recording, public-link verification.

No person should edit evaluator formulas independently in a notebook.

## 10. Test plan

### Mandatory unit/property tests

- Canonical variable order is exactly `i=3*d+p`.
- Every candidate path begins/ends at its demand endpoints and every edge exists.
- Incidence-based and direct path-based load calculations agree.
- All 81 one-hot assignments decode round-trip.
- Scenario normalizers match stored extrema and handle zero ranges.
- Feasibility counts and optimum tie sets match Section 4.
- H and R exact trajectories match Section 4 with lexicographic ties.
- QUBO and direct weighted objectives differ only by the recorded convention/offset.
- Ising substitution `x=(1-Z)/2` agrees on all 4096 bitstrings.
- Calibrated `M` produces a strictly positive invalid-ground gap.
- In aligned mode, circuit-energy and optimizer-energy evaluators agree with `E_aligned` on all 4096 states.
- Calibrated `Lambda` leaves every aligned ground state structurally valid and jointly capacity-feasible; all ties are checked.
- Positive affine scaling preserves the full ordering/tie set and is not credited with a resource reduction.
- Bit decoding is verified with a known basis-state test before using real samples.
- Repeated sampled bitstrings aggregate counts correctly before probabilities and acceptance rates are calculated.

### Integration tests

- One p=1 synthesis produces a saved `qprog` and non-null metrics.
- One optimizer run returns a non-empty list of `(cost, params)` pairs.
- One final sample produces a table with counts summing to the declared shot total.
- An aligned-mode smoke test, if attempted, reports its joint-feasible probability rather than asserting feasibility from construction.
- A quantum run with no accepted sample produces `NO_FEASIBLE_SAMPLE` and no fabricated assignment.
- Saved JSON/CSV records can regenerate every plot without a Classiq login.

## 11. Required experiment matrix

| Experiment | Inner domain | Purpose |
|---|---|---|
| Shortest path | One-hot only; report overflow | Simple routing reference |
| Load-aware greedy | Declare which scenarios are considered | Practical heuristic |
| Exact nominal | Nominal-feasible | Stress a nominal plan out of scenario |
| Exact unrestricted weighted H/R | All one-hot routes | True Hamiltonian ground reference |
| Exact joint-feasible uniform H | Joint feasible | Supplied static cost control |
| Exact joint-feasible uniform R | Joint feasible | Critical normalization control |
| Exact pure minimax R | Joint feasible | Best pure robust plan |
| Exact adaptive H and R | Joint feasible | Classical outer-loop behavior |
| Exact aligned H/R, optional | All bitstrings | Certify calibrated `M`, `Lambda`, and aligned ground-state feasibility |
| QAOA uniform H and R | Measured routes, postselected | Quantum static controls |
| QAOA adaptive H | Measured routes, postselected | Main quantum experiment |
| QAOA aligned H, optional | Measured routes, still postselected | Test target alignment versus added circuit cost; not a feasibility guarantee |
| Uniform random bitstrings | Same total final shots and filters | Tests whether QAOA beats uninformed sampling |
| Uniform random valid routes | Same sample budget | Stronger classical sampling control |

The matched-regret quantum adaptive run and the digitally constrained QAOA variant are optional after this matrix.

For comparisons against a three-solve adaptive run, aggregate static-run budgets to the same total optimizer and final-readout budget or clearly label the mismatch.

## 12. Result schema and plots

Each run directory should contain:

- `manifest.json`: schema version, code/config hash, timestamp, interpreter/environment path, Python and SDK versions, authentication smoke-test result, backend, seed, objective and energy mode, weights, `M`, `Lambda` if used, phase offset/scale, shots, optimizer cap, quantile.
- `qubo.json`: offset, linear and quadratic coefficients, variable map, validation errors, invalid-ground gap, and aligned-ground feasibility audit when applicable.
- `circuit.json` or serialized `qprog`: synthesis artifact and resource metrics.
- `optimizer.json`: complete cost/parameter trace.
- `samples.csv`: raw decoded states, bitstrings, counts, probabilities, validity, feasibility, scenario costs, and regrets.
- `summary.json`: status, selected plan, exact gap, acceptance rates, optimum probability, runtime, warnings.

Required figures:

1. Network topology with the selected route highlighted per demand.
2. Scenario weights before each adaptive solve.
3. Current and best-so-far worst regret by solve index.
4. Per-scenario regret comparison for nominal, static H, static R, and adaptive H plans.
5. One-hot and joint-feasible probability mass for QAOA versus random bitstrings.
6. Optimizer cost trace for representative QAOA runs.

Do not use a 4096-bar raw-bitstring chart in the pitch. Show the top accepted routes plus aggregated invalid/one-hot/joint-feasible mass.

## 13. Risk register and responses

| Risk | Trigger | Response |
|---|---|---|
| Authentication unavailable | First SDK call fails | Authenticate immediately; if unresolved, preserve exact pipeline and record the platform blocker |
| QAOA targets infeasible ground | Joint-feasible probability is poor or unrestricted ground dominates | Show matched unrestricted control; optionally test the common-energy digital penalty while retaining postselection |
| One-hot acceptance is poor | Less than a useful number of accepted shots | Verify mapping/sign/M; one bounded retry; consider constraint-preserving mixer only as future work |
| Synthesis is too deep/wide | Metrics or timeout are unacceptable | Keep `p=1`, remove the optional digital predicate, simplify arithmetic/control logic, and use the default simulator; do not present coefficient scaling as a depth remedy |
| Adaptive claim is weak | Uniform R already matches minimax | Present this as a control finding; novelty is the verified adaptive architecture |
| Random sampling matches QAOA | Best-result metrics tie | Emphasize full probability mass, exact gaps, resource costs, and honest limitation |
| Run budget expands | Repeated seeds or retries consume time/quota | One integration seed first; predeclare one retry; cache every successful artifact |
| Demo depends on login/network | Slides or notebook need live services | Record video and regenerate plots entirely from saved artifacts |

## 14. Feature cuts

Cut in this order if schedule slips:

1. `p=2` and hardware-backend comparison.
2. Digital capacity-predicate variant.
3. Additional quantum seeds beyond one.
4. Quantum execution over the generalization grid.
5. Link-failure recovery, min-cut analysis, and route churn.

Never cut the exact ground truth, QUBO/Ising checks, static regret control, random controls, raw quantum evidence, or public presentation test. Those are the credibility core.

## 15. Definition of done

The full MVP is done when another team member can:

1. Reproduce the 81-route ground truth.
2. Verify evaluator-QUBO and QUBO-Ising agreement.
3. Inspect a real Classiq-synthesized p=1 program and its measured resources.
4. Re-run at least one quantum optimization and decode its raw sample distribution.
5. Follow all three adaptive H solves through the same solver-agnostic outer loop.
6. Compare against uniform R, exact, greedy, and random controls.
7. Trace every plot and spoken number to a saved artifact.
8. Open the submitted presentation and embedded video without authentication.

If the optional aligned lane is claimed, another team member must also reproduce the `Lambda` audit, verify equality of circuit/optimizer/reference energies, and inspect the measured feasible probability. Ground-state alignment alone is not completion evidence for a finite-depth run.

The fallback MVP is acceptable if it contains one verified fixed Classiq QAOA solve plus the exact adaptive experiment and clearly states that the quantum adaptive loop or capacity-aligned variant was not completed.

## 16. Recommended pitch thesis

> Q-ERA tests Classiq QAOA as the discrete route-selection engine inside an adaptive multi-scenario routing workflow. We verify the Hamiltonian exhaustively, filter or encode operational feasibility explicitly, and benchmark the measured quantum distribution against exact and random controls. The experiment shows what the adaptive mechanism and the quantum inner solver each contribute - including when a static regret objective is already sufficient.

## 17. References

- `../Q_ERA_Standalone_Team_Plan.md` - assessed source proposal and deterministic fixture.
- `../QUBIT Hackathon 2026 - Challenge Briefs.pdf` - organizer challenge, deliverables, and judging criteria.
- `../QUBIT Hackathon 2026 - Participant Brief.pdf` - event schedule and submission format.
- [Classiq QAOA](https://docs.classiq.io/explore/algorithms/search_and_optimization/QAOA/qaoa) - cost-phase, mixer, and parameterized ansatz pattern.
- [Classiq variational_minimize](https://docs.classiq.io/sdk-reference/execution#variational_minimize-3) - current optimization API.
