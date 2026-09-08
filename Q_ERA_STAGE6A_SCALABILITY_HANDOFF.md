# Q-ERA Stage 6A — Scalability & Generalization Handoff

**Project:** Q-ERA — Quantum-Enabled Resilient Adaptation  
**Purpose:** optional post-MVP scalability study  
**Status of v1.1:** **FROZEN — Stages 0–5 are complete and must not be modified**  
**Target:** strengthen the hackathon criterion **Quantum fit, scalability and benchmarking** without destabilizing the validated implementation.

---

# 1. Objective

The v1.1 MVP establishes correctness and auditability on a small fixture:

- \(D=4\) traffic demands
- \(K=3\) candidate paths per demand
- \(S=3\) training scenarios
- \(DK=12\) logical route-choice bits
- \(K^D=81\) structurally valid route assignments
- \(2^{DK}=4096\) raw bitstrings
- exact classical truth is available
- QUBO/Ising mapping is exhaustively verified
- Classiq \(p=1\) QAOA has been implemented
- static and adaptive controls have been tested

Stage 6A asks a different question:

> **How does the Q-ERA formulation and quantum implementation behave as the number of routing decisions increases?**

This is **not** a quantum-advantage experiment.

The goal is to produce measured evidence for:

1. formulation scaling;
2. QUBO interaction scaling;
3. Classiq synthesis/resource scaling;
4. QAOA sampling/solution-quality scaling where execution remains practical;
5. classical benchmark behavior on larger instances.

---

# 2. Frozen invariants

Stage 6A must reuse the existing v1.1 implementation.

Do **not** alter:

- the QUBO coefficient convention;
- the one-hot route encoding;
- the shared evaluator;
- the scenario-cost definitions;
- latency/congestion normalization logic;
- capacity-feasibility definitions;
- regret definitions;
- sample decoding;
- postselection rules;
- the adaptive-loop implementation;
- the Classiq \(p=1\) ansatz;
- result schemas.

Initial scaling experiments must keep:

\[
K=3,\qquad S=3,\qquad p=1.
\]

Only the number of demands \(D\) should change first.

Any later experiment that changes \(K\), \(S\), \(p\), mixer type, or capacity encoding must be labeled as a **separate extension**, not part of Stage 6A core evidence.

---

# 3. Scalability dimensions

Do not use the word "scalable" as one undifferentiated claim.

Stage 6A must report four separate scaling dimensions.

## 3.1 Formulation scaling

With \(D\) demands and \(K\) candidate paths per demand:

\[
N_{\text{logical bits}} = DK.
\]

For fixed \(K=3\):

\[
N_{\text{logical bits}}=3D.
\]

The number of structurally valid route assignments is:

\[
N_{\text{valid}}=K^D=3^D.
\]

The full binary Hilbert space contains:

\[
N_{\text{raw}}=2^{DK}=2^{3D}.
\]

The one-hot subspace fraction is:

\[
f_{\text{one-hot}}
=
\frac{K^D}{2^{DK}}
=
\left(\frac{K}{2^K}\right)^D
=
\left(\frac38\right)^D.
\]

This shrinking fraction is a real scalability limitation of the current one-hot + transverse-\(X\)-mixer implementation.

---

## 3.2 QUBO interaction scaling

Record:

- number of logical bits;
- number of nonzero linear coefficients;
- number of nonzero quadratic couplings;
- maximum possible quadratic pairs:

\[
\binom{DK}{2};
\]

- coupling density:

\[
\rho_Q
=
\frac{\#\{J_{ij}\ne0\}}
{\binom{DK}{2}};
\]

- mean interaction degree;
- maximum interaction degree.

Shared candidate-path edges produce pairwise interactions. If larger instances become highly coupled, the QUBO may approach dense connectivity even though logical width grows only linearly.

---

## 3.3 Quantum resource scaling

For every size that Classiq can synthesize, record:

- logical route-choice bits;
- synthesized qubit count;
- circuit depth;
- total gate count;
- two-qubit gate count;
- synthesis status;
- synthesis wall-clock time if available.

**Synthesis-only results are valid scalability evidence.**

Do not require statevector/QAOA execution for every problem size.

---

## 3.4 Quantum solution-quality scaling

Only for sizes where actual QAOA execution is practical, record:

- one-hot-valid probability mass;
- jointly capacity-feasible probability mass;
- best feasible objective;
- best feasible regret;
- gap to exact optimum or best-known classical solution;
- probability of sampling the exact/best-known route when known;
- optimizer iteration count;
- shots;
- runtime with simulator/backend caveat.

This is the most important test of whether the present ansatz degrades as \(D\) increases.

---

# 4. Why simulator scaling must be interpreted carefully

The classical statevector simulator scales with:

\[
2^{DK}.
\]

For \(K=3\):

| \(D\) | Logical bits | Valid routes \(3^D\) | Full states \(2^{3D}\) |
|---:|---:|---:|---:|
| 4 | 12 | 81 | 4,096 |
| 5 | 15 | 243 | 32,768 |
| 6 | 18 | 729 | 262,144 |
| 7 | 21 | 2,187 | 2,097,152 |
| 8 | 24 | 6,561 | 16,777,216 |
| 10 | 30 | 59,049 | 1,073,741,824 |
| 12 | 36 | 531,441 | 68,719,476,736 |

Therefore the simulator may become difficult **before** exhaustive enumeration of \(3^D\) valid route assignments becomes difficult.

Do not interpret this as:

> "The quantum algorithm does not scale because statevector simulation does not scale."

The correct interpretation is:

> Classical emulation becomes expensive with qubit count, while the current quantum ansatz also has a genuine feasible-subspace inefficiency because the transverse-\(X\) mixer explores the full \(2^{DK}\) binary space.

Both facts should be reported separately.

---

# 5. Core experiment grid

Use deterministic seeded instances.

Required initial sizes:

\[
\boxed{
D\in\{4,5,6,8\}
}
\]

with:

\[
K=3,\qquad S=3.
\]

Additional sizes may be added only if the core grid is complete.

Recommended execution policy:

| Size | Classical analysis | QUBO analysis | Classiq synthesis | QAOA execution |
|---|---|---|---|---|
| \(D=4\) | required | required | required | already complete / reference |
| \(D=5\) | required | required | required | attempt |
| \(D=6\) | required | required | required | **priority larger execution** |
| \(D=8\) | required | required | required if practical | optional |
| \(D>8\) | optional | optional | useful if practical | not required |

The **highest-value additional quantum point is \(D=6\)**:

\[
18\text{ logical bits},\qquad 3^6=729\text{ valid routes}.
\]

This is meaningfully larger than the MVP while still potentially executable.

---

# 6. Larger-instance generation

Do not generate arbitrary random graphs that accidentally remove the routing trade-offs.

Each larger instance must preserve:

1. multiple demands competing for shared bottleneck edges;
2. at least three candidate paths per demand;
3. nontrivial latency-vs-congestion trade-offs;
4. demand-surge scenario;
5. capacity-degradation scenario;
6. at least some jointly feasible solutions.

Preferred generation strategy:

1. start from the validated structural motif of the v1.1 fixture;
2. add source/destination pairs and/or repeated corridor structures;
3. introduce shared central bottlenecks;
4. use deterministic random seeds only for controlled perturbations;
5. verify candidate paths remain distinct and loop-free.

Every generated instance must save:

```text
instance_id
seed
D
K
S
nodes
edges
capacities
latencies
demands
candidate_paths
scenario_parameters
```

---

# 7. Instance acceptance checks

Before any QUBO or quantum work, verify:

- all demands have exactly \(K=3\) candidate paths;
- all paths connect the correct source/destination;
- all path edges exist;
- candidate paths are distinct;
- nominal scenario has feasible assignments;
- demand-surge scenario has feasible assignments;
- capacity-degradation scenario has feasible assignments;
- jointly feasible assignments exist, when exact enumeration is still practical;
- the scenarios create conflicting optimization pressure.

Reject and regenerate an instance if:

- all scenarios share the same optimum trivially;
- degradation makes all routes infeasible;
- no candidate paths share resources;
- congestion terms become essentially zero or constant.

---

# 8. Classical benchmarking policy

Exact enumeration is a **ground-truth tool**, not a required scalable baseline.

## 8.1 Small sizes

Use exhaustive enumeration while inexpensive.

For \(K=3\):

\[
3^D
\]

is still modest for several additional \(D\) values.

Record exact truth when practical.

## 8.2 Larger sizes

When exhaustive truth is no longer appropriate, use a portfolio of classical methods.

Recommended hierarchy:

1. MILP / MIQP / CP-SAT formulation if convenient;
2. load-aware greedy;
3. local search;
4. simulated annealing;
5. random valid-route sampling.

The exact solver is preferred when practical, but Stage 6A must **not stall** waiting for a perfect exact solution at larger sizes.

For non-exact baselines, record:

```text
best-known objective
best-known worst regret
runtime
seed
solver parameters
status / optimality certificate if available
```

Do not label a heuristic result "optimal."

---

# 9. Required classical scaling metrics

For every \(D\), save:

- number of nodes;
- number of edges;
- \(D\);
- \(K\);
- \(S\);
- \(DK\);
- \(K^D\);
- exact-enumeration runtime when performed;
- greedy runtime;
- local-search / simulated-annealing runtime when performed;
- exact or best-known objective;
- exact or best-known worst-case regret;
- feasibility rate of random valid assignments;
- joint-feasibility rate among valid assignments.

These provide the classical side of the scalability story.

---

# 10. Required QUBO scaling metrics

For each instance, build the same v1.1 weighted objective.

Save:

```text
logical_bits
nonzero_linear
nonzero_quadratic
possible_quadratic_pairs
quadratic_density
mean_interaction_degree
max_interaction_degree
one_hot_penalty_M
qubo_energy_range
```

If exact 4096/32768/etc. whole-bitspace verification becomes expensive, preserve the validated coefficient-construction tests and test a large deterministic sample of bitstrings plus all one-hot assignments.

Do not weaken the v1.1 test suite for the original \(D=4\) fixture.

---

# 11. Classiq synthesis experiment

For each selected \(D\):

1. build the weight-specific \(p=1\) model;
2. synthesize using the same basic Classiq construction as v1.1;
3. do not introduce new width/depth constraints initially;
4. save the synthesized program;
5. extract resource metrics.

Required output:

```text
instance_id
D
logical_bits
synthesized_qubits
depth
gate_count
two_qubit_gate_count
synthesis_runtime
synthesis_status
warning
```

If synthesis fails:

- record the failure;
- do not redesign v1.1;
- optionally retry once after confirming the failure is not an environment/authentication issue;
- then mark that size as the current synthesis boundary.

A synthesis failure at a larger size is still useful evidence if documented honestly.

---

# 12. QAOA execution subset

Do **not** run the full 3-step adaptive Q-ERA loop at every scale initially.

For larger instances, use a static representative weighted objective first.

Recommended first test:

\[
w=(1/3,1/3,1/3).
\]

Use the same:

- \(p=1\);
- optimizer;
- shot policy;
- decoding;
- postselection;
- evaluator;

as the frozen implementation unless resource limits require a clearly recorded reduced budget.

For \(D=5\) and \(D=6\), attempt:

1. one uniform-weight QAOA solve;
2. final sample distribution;
3. comparison against random controls and classical benchmark.

Run the adaptive outer loop on \(D=6\) **only if the static solve is stable and time remains**.

---

# 13. Matched controls for larger quantum runs

For every executed larger QAOA instance, compare against:

### Control A — uniform random bitstrings

Same final sample count.

Apply exactly the same:

- one-hot filter;
- capacity filter;
- metric evaluation.

### Control B — uniform random valid routes

Sample directly from the \(K^D\) one-hot route space.

Use the same number of samples.

This is a stronger control because it removes the obvious one-hot penalty disadvantage.

### Control C — classical heuristic

At minimum, use load-aware greedy.

Prefer additionally:

- simulated annealing;
- local search;
- exact / MILP best-known route where practical.

---

# 14. Required QAOA scaling metrics

For each actually executed larger instance, report:

\[
P_{\text{one-hot}}
\]

and

\[
P_{\text{joint-feasible}}.
\]

Also report:

- best feasible weighted objective;
- best feasible worst-case regret;
- gap to exact/best-known classical solution;
- probability mass on the best-known route if identifiable;
- probability mass within a declared approximation threshold;
- optimizer trace length;
- shots;
- seed;
- runtime;
- circuit resources.

Do not use "best sample found" as the only quantum-quality metric.

---

# 15. Primary scaling plots

Generate from saved records only.

## Plot 1 — quantum width

x-axis:

\[
D
\]

y-axis:

- logical route-choice bits;
- synthesized qubit count.

## Plot 2 — circuit resources

x-axis:

\[
D
\]

y-axis:

- circuit depth;
- two-qubit gate count.

If scales differ strongly, use separate panels/figures rather than an unreadable mixed axis.

## Plot 3 — QUBO interaction structure

x-axis:

\[
D
\]

y-axis:

- number of nonzero quadratic couplings;
- or coupling density.

## Plot 4 — feasible probability

For sizes with QAOA execution:

x-axis:

\[
D
\]

y-axis:

\[
P_{\text{one-hot}},\qquad
P_{\text{joint-feasible}}.
\]

Compare QAOA with:

- uniform random bitstrings;
- uniform random valid routes when applicable.

## Plot 5 — solution quality

For executed sizes:

x-axis:

\[
D
\]

y-axis:

- relative objective gap;
- or worst-case-regret gap to best-known classical benchmark.

---

# 16. Scalability claims allowed

If supported by results, use:

> Q-ERA's candidate-path formulation requires \(DK\) logical route-choice bits, so width grows linearly with the number of demands for fixed candidate count.

Use:

> Adding robustness scenarios changes the weighted Hamiltonian coefficients and classical evaluation workload but does not replicate the route-choice register.

Use:

> The current one-hot \(X\)-mixer ansatz has a known scaling limitation: the structurally valid fraction of the binary Hilbert space shrinks as \((K/2^K)^D\).

Use:

> Our scaling study measures where synthesis resources and feasible sampling begin to deteriorate rather than extrapolating from a 12-bit fixture.

Use:

> Statevector-simulator limits are classical-emulation limits and should be distinguished from real quantum-hardware width/depth requirements.

---

# 17. Claims not allowed

Do not say:

- "Q-ERA has polynomial runtime."
- "QAOA scales efficiently to AT&T-sized routing."
- "18 qubits proves industrial scalability."
- "Statevector simulation failure proves quantum advantage."
- "QAOA beats classical routing" unless the measured benchmark actually shows it.
- "Quantum advantage" based on simulator results.
- "The path encoding always remains compact" without noting dependence on \(K\).
- "Adding scenarios is free." It does not increase route bits, but it increases objective construction/evaluation complexity and can affect circuit density/coefficients.

---

# 18. Known scaling bottleneck and future remedy

The current ansatz uses:

- one-hot variables;
- \(|+\rangle^{\otimes DK}\) initialization;
- transverse-\(X\) mixer;
- one-hot penalty.

The valid fraction is:

\[
\left(\frac{K}{2^K}\right)^D.
\]

For \(K=3\):

\[
\left(\frac38\right)^D.
\]

This is expected to reduce useful probability mass as \(D\) increases.

The principal future quantum improvement is:

### Constraint-preserving / one-hot mixer

Prepare each demand inside its \(K\)-state one-hot subspace and use an XY-style or other constraint-preserving mixer that moves amplitude only between the valid path choices for that demand.

Conceptually:

```text
Current MVP:
2^(DK) binary space
    -> X mixer
    -> penalty
    -> postselection

Future:
K^D path-selection subspace
    -> one-hot-preserving mixer
    -> all explored states structurally valid
```

Do **not** implement this during Stage 6A unless all required scaling evidence is already complete.

A compressed route-index encoding using approximately

\[
D\lceil\log_2 K\rceil
\]

bits is another possible future direction, but it complicates cost construction and is not part of Stage 6A.

---

# 19. Candidate-path scaling limitation

The width result

\[
DK
\]

assumes small \(K\).

As larger networks become more complex, a fixed \(K\) may omit useful routing alternatives.

Therefore report the trade-off:

> Smaller \(K\) reduces quantum width but restricts routing flexibility; larger \(K\) improves route coverage but increases decision width and QUBO coupling.

Possible future architecture:

- start with small \(K\);
- solve;
- detect congested/poorly represented demands;
- generate additional classical candidate paths;
- re-solve.

This resembles adaptive path generation / column generation.

Do not implement in Stage 6A.

---

# 20. Stage 6A execution order

## Step A — freeze and copy

- tag / checkpoint the completed v1.1 state;
- create a new Stage 6A branch or worktree;
- do not edit v1.1 evidence artifacts.

### GO A

The full v1.1 test suite passes unchanged.

---

## Step B — parameterize instance size

Refactor only what is necessary so the existing pipeline accepts:

```python
D = variable
K = 3
S = 3
```

Do not change evaluator formulas.

### GO B

The parameterized implementation reproduces all original \(D=4\) reference values.

If not: **STOP**.

---

## Step C — generate scaling instances

Create deterministic \(D=5,6,8\) instances.

Run acceptance checks.

### GO C

Every accepted instance has:

- 3 candidate paths per demand;
- meaningful shared-resource coupling;
- feasible routes in every scenario;
- scenario trade-offs.

---

## Step D — classical/QUBO scaling

For each size:

- run exact enumeration where practical;
- run heuristic baselines;
- build QUBO;
- calculate interaction metrics.

### GO D

All records are saved and can regenerate tables without Classiq access.

---

## Step E — Classiq synthesis scaling

Attempt synthesis in order:

\[
D=5\rightarrow6\rightarrow8.
\]

Stop increasing size after a meaningful synthesis/resource boundary appears or time budget is reached.

### GO E

At least two post-MVP synthesis points are recorded, preferably including \(D=6\).

---

## Step F — larger QAOA execution

Priority:

1. \(D=5\);
2. \(D=6\).

Execute one static uniform-weight solve first.

### GO F

A larger run is considered useful if it produces a saved sample distribution and one of:

- measurable one-hot/feasible probability;
- objective concentration above random control;
- evidence of feasible-probability collapse.

A negative result is still useful scalability evidence.

---

## Step G — plots and interpretation

Produce the five scaling figures or the useful subset supported by data.

Do not begin new algorithmic features after this point.

---

# 21. Stop conditions

Stage 6A must stop if any of the following becomes true:

- v1.1 regression appears;
- less than the reserved submission/evidence time remains;
- repeated Classiq execution failures are consuming the run budget;
- synthesis/execution debugging starts requiring architectural redesign;
- the team still lacks stable final plots/demo for the core MVP.

In those cases:

> stop Stage 6A, preserve all completed scaling artifacts, and return to submission preparation.

The Stage 6A study is optional. The validated v1.1 result remains the submission fallback.

---

# 22. Minimum successful Stage 6A outcome

Stage 6A is already valuable if it achieves:

1. deterministic \(D=5,6,8\) instances;
2. QUBO structural metrics for all;
3. at least two larger Classiq synthesis points;
4. one actual larger QAOA sample distribution, ideally \(D=6\);
5. classical controls;
6. one resource-scaling plot;
7. one feasible-probability or solution-quality scaling plot.

No quantum advantage is required.

---

# 23. Strong successful outcome

A strong Stage 6A result would show:

- \(DK\) logical width growing linearly;
- measured QUBO connectivity growth;
- Classiq depth / two-qubit gate growth;
- a working \(D=6\), \(18\)-logical-bit QAOA run;
- QAOA outperforming uniform random bitstrings or random valid-route sampling on probability mass / solution quality;
- measurable decline in one-hot or feasible probability with \(D\);
- explicit identification of the current ansatz's scaling boundary.

That is a credible and mature scalability story even if strong classical optimization remains superior.

---

# 24. Judging narrative

Recommended concise wording:

> **Q-ERA separates scalable problem structure from current proof-of-concept limitations. For fixed \(K\), the path-selection register grows as \(DK\), and adding robustness environments does not replicate the decision register. We then measure—not assume—how QUBO connectivity, synthesized depth, two-qubit gates, feasible sampling probability, and solution quality evolve as the routing problem grows. The current penalty-based one-hot ansatz exposes a clear sampling bottleneck, motivating a future constraint-preserving mixer.**

If QAOA remains useful at \(D=6\):

> **We extended the validated 12-bit fixture to an 18-logical-bit routing instance and measured both circuit resources and sampled solution quality against classical and random controls.**

If QAOA quality collapses:

> **The scaling experiment identifies feasible-subspace sampling as the first bottleneck of the present ansatz. This is a useful architectural result: the candidate-path formulation itself remains compact, while the generic mixer is the component requiring redesign.**

Both are credible outcomes.

---

# 25. Deliverables

Stage 6A should create:

```text
artifacts/scaling/
    instances/
    classical/
    qubo/
    circuits/
    qaoa/
    tables/
    figures/
```

Required summary files:

```text
scaling_manifest.csv
scaling_classical.csv
scaling_qubo.csv
scaling_synthesis.csv
scaling_qaoa.csv
SCALABILITY_FINDINGS.md
```

`SCALABILITY_FINDINGS.md` must state:

1. what sizes were tested;
2. which were exact;
3. which were synthesized;
4. which were actually executed with QAOA;
5. what classical baselines were used;
6. where current bottlenecks appeared;
7. which claims are supported;
8. which remain future work.

---

# 26. Definition of done

Stage 6A is done when another team member can:

- reproduce the larger deterministic instances;
- regenerate classical/QUBO scaling tables;
- inspect saved Classiq resource metrics;
- reproduce at least one larger quantum sample analysis if execution succeeded;
- regenerate all scaling plots without rerunning Classiq;
- distinguish formulation scaling, simulator scaling, and quantum-algorithm scaling;
- explain why the current one-hot \(X\)-mixer is the major known bottleneck;
- present the scaling findings without claiming quantum advantage.

---

# 27. Final instruction to implementation agent

> **Do not redesign Q-ERA. Do not reopen validated Stages 0–5. Stage 6A is a bounded evidence-gathering extension. First parameterize the frozen implementation, reproduce the original fixture, generate larger deterministic instances, measure classical/QUBO/synthesis scaling, and only then attempt a small number of larger QAOA executions. A negative scaling result is valid evidence. The objective is a defensible scalability analysis, not a forced claim of quantum superiority.**
