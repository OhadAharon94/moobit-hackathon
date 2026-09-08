# Holy QOW — Dual-Agent Research Handoff
## Track A: Stage 6B Constraint-Preserving QAOA
## Track B: Evolution / Generalization Diagnosis

**Status:** v1.1 Stages 0–5 complete; Stage 6A complete; Post-6A Steps 0–2 complete.  
**Current decision:** D=6 adaptive QAOA Step 3 remains **NO-GO**.  
**Execution model:** two independent agents may work in parallel.  
**Critical rule:** **Do not combine the new mixer with adaptive scenario reweighting until both tracks independently pass validation and the user explicitly approves a combined experiment.**

---

# 1. Why these two tracks

Post-6A evidence established:

- The current \(|+\rangle\) + transverse-\(X\) QAOA loses most probability outside the one-hot routing subspace.
- Conditional on one-hot validity, QAOA has **not** shown significant superiority over matched uniform-valid sampling.
- Five D=6 seeds showed a repeated advantage over uninformed random bitstrings on best feasible objective/regret, but one-hot and feasible masses were unstable.
- The original adaptive route generalized worse than static uniform multi-scenario routing on the held-out scenarios.

Therefore two separate questions must be answered:

### Track A — quantum question
Can a one-hot-preserving QAOA ansatz eliminate structural waste and learn a useful distribution **inside the valid routing manifold**?

### Track B — evolutionary question
Why did adaptive scenario reweighting generalize worse? Is the cause:
- too few environments;
- excessive selection pressure;
- inadequate outer-loop length;
- environment-weight collapse / over-specialization;
- or a mismatch between the training regret objective and operational robustness?

---

# 2. Shared frozen foundations

Both agents must reuse the validated implementation.

Do not redefine:
- graph/evaluator semantics;
- path ordering;
- cost components;
- normalization;
- capacity feasibility;
- regret;
- frozen v1.1/Stage-6A/Post-6A artifacts.

Before new work, run the relevant frozen test suites.

Use separate branches/worktrees and artifact roots:

```text
Agent A branch: stage6b-constraint-mixer
Agent B branch: evolution-ablation

artifacts/stage6b/
artifacts/evolution_ablation/
```

No existing evidence may be overwritten.

---

# 3. Coordination boundary

## Agent A must NOT:
- change scenario weights;
- run multiplicative adaptation;
- tune \(\eta,T,S,\rho\);
- claim resilience/generalization improvements.

## Agent B must NOT:
- modify QAOA;
- use the new mixer;
- run Classiq quantum jobs;
- attribute classical adaptation effects to quantum computation.

The agents report separately.

---

# 4. AGENT A — Stage 6B Constraint-Preserving QAOA

## Research question

> If QAOA is forced to remain in the valid one-hot route-selection space, does its probability distribution favor high-quality routes more strongly than uniform valid-route sampling?

Use **fixed uniform scenario weights only**:

\[
w=(1/3,1/3,1/3).
\]

No adaptive outer loop.

---

## 4.1 One-hot representation

For each demand \(d\) with \(K=3\) route bits:

\[
(x_{d,0},x_{d,1},x_{d,2}),
\]

the valid basis states are:

\[
|100\rangle,\ |010\rangle,\ |001\rangle.
\]

Implement:
1. one-hot-preserving initial state preparation;
2. a mixer that preserves Hamming weight one.

A suitable conceptual mixer is:

\[
H_M^{(d)}
=
\sum_{p<q}
(X_{d,p}X_{d,q}+Y_{d,p}Y_{d,q}).
\]

An equivalent Classiq-native constrained mixer is acceptable if its preservation property is verified.

---

## 4.2 Execution order

### A0 — Regression
Run frozen tests and reproduce existing D=4 references.

**STOP on regression.**

### A1 — Mixer correctness at one demand
For each valid basis state and multiple nontrivial mixer angles:
- prepare the basis state;
- apply the mixer;
- verify zero support outside Hamming weight one.

Required:

\[
P(\text{Hamming weight}=1)=1
\]

within numerical/sampling tolerance.

### A2 — Full D=4 structural preservation
Run the full 4-demand ansatz without optimization and verify every sampled demand register is one-hot.

Expected:

\[
P(\text{structurally valid})\approx100\%.
\]

### A3 — Initial-state fairness
If initialization is intended to be uniform over all valid route assignments, verify that it is approximately uniform before applying optimization.

For \(D=4\):

\[
3^4=81
\]

valid routes.

A mixer-only / \(p=0\)-equivalent sample should reproduce uniform-valid behavior within finite-shot tolerance.

### A4 — Cost compatibility
On all 81 D=4 valid assignments, verify that the constrained-mode cost ranking matches the frozen classical/QUBO objective exactly.

If the one-hot penalty is removed in constrained mode, verify:

\[
E_{\text{constrained}}(x)=E_{\text{base}}(x)-\text{constant}
\]

or at minimum that all valid-state energy differences/orderings agree.

Do not change the routing objective while changing the mixer.

### A5 — D=4 constrained QAOA
Run \(p=1\), uniform weights.

Compare against:
- existing transverse-\(X\) QAOA;
- uniform random valid routes;
- exact weighted optimum.

Metrics:
- one-hot probability;
- joint-feasible probability;
- near-optimal probability;
- objective distribution;
- best feasible gap;
- best regret;
- exact-optimum probability;
- circuit qubits/depth/gates/2Q gates.

### A6 — Repeatability
Run at least 3 independent optimizer seeds at D=4.

Only proceed to D=6 if:
- preservation tests pass;
- synthesis/execution is stable;
- results are reproducible enough to interpret.

### A7 — D=6
If approved by the above gate, repeat on frozen D=6:

- 3 seeds minimum;
- 5 preferred if practical.

Keep the same static objective and \(p=1\).

---

# 5. Agent A success criteria

**Do not count \(P(\text{one-hot})\approx100\%\) as optimization success; it is guaranteed by construction.**

Meaningful evidence requires one or more of:

1. near-optimal probability above uniform-valid sampling;
2. objective distribution shifted toward lower cost;
3. matched-valid-sample best-gap/regret improvement;
4. larger exact/best-known optimum probability;
5. reproducibility across seeds.

Use fair valid-sample budgets.

If constrained QAOA is indistinguishable from uniform-valid sampling, report that.

---

# 6. Agent A statistical comparison

For every constrained-QAOA seed:

- generate \(\ge1000\) uniform-valid batches matched to the same final valid-sample count;
- compare:
  - best objective gap;
  - best regret;
  - near-optimal fraction;
  - feasible fraction.

Report empirical p-values / percentile rank.

Also compare full valid-state cost distributions when possible.

---

# 7. Agent A resource comparison

Compare X-mixer vs constrained mixer at the same D and \(p\):

- logical/synthesized qubits;
- depth;
- gates;
- 2Q gates;
- synthesis runtime;
- optimizer runtime.

A better valid distribution with huge circuit overhead must be reported as a tradeoff.

---

# 8. Agent A mandatory correctness gates

Before interpreting results, confirm:

- [ ] frozen tests pass;
- [ ] single-demand mixer preserves Hamming weight one;
- [ ] full D=4 samples are structurally valid;
- [ ] initial distribution is understood and tested;
- [ ] valid-state cost ordering matches frozen objective;
- [ ] bit ordering/decoding is verified;
- [ ] counts sum to shot total;
- [ ] poor/failed optimizer seeds are retained.

---

# 9. Agent A deliverables

Create:

```text
artifacts/stage6b/
    stateprep/
    mixer_validation/
    d4/
    d6/
    tables/
    figures/
```

Required:

```text
stage6b_stateprep_validation.json
stage6b_mixer_preservation.json
stage6b_d4_results.csv
stage6b_d4_seed_summary.csv
stage6b_d6_results.csv           # if attempted
stage6b_d6_seed_summary.csv      # if attempted
STAGE6B_FINDINGS.md
```

Main report must answer:

1. Did the mixer preserve one-hot structure exactly?
2. What circuit overhead did it introduce?
3. Did constrained QAOA beat uniform-valid sampling?
4. Was any advantage reproducible?
5. Is D=6 justified/successful?

---

# 10. AGENT B — Evolution / Generalization Diagnosis

## Research question

> Why did exact adaptive scenario reweighting generalize worse than static uniform weighting on the frozen held-out test?

This track is **classical only**.

Use the exact inner best-response solver.

No new quantum jobs.

---

# 11. Agent B hypotheses

## H1 — Too few training environments
Test:

\[
S\in\{3,5,8,12\}.
\]

Training environments must be diverse in location and severity.

## H2 — Selection pressure too strong
Test:

\[
\eta\in\{0,\ 0.1,\ 0.25,\ 0.5,\ 1.0,\ 2.0\}.
\]

\(\eta=0\) is the static/uniform control.

## H3 — Outer-loop length
Test:

\[
T\in\{1,2,3,5,10\}.
\]

Interpret \(T\) jointly with \(\eta\), not in isolation.

## H4 — Environmental-weight collapse / over-specialization
Test diversity mixing:

\[
w^{(t+1)}
=
(1-\rho)\tilde w^{(t+1)}
+
\rho\frac{\mathbf 1}{S},
\]

with:

\[
\rho\in\{0,\ 0.1,\ 0.25,\ 0.5\}.
\]

where:

\[
\tilde w_s^{(t+1)}
=
\frac{w_s^{(t)}e^{\eta\bar r_s^{(t)}}}
{\sum_jw_j^{(t)}e^{\eta\bar r_j^{(t)}}}.
\]

## H5 — Regret/feasibility mismatch
Do not change the fitness function initially.

For diagnosis only, record:
- regret;
- feasibility;
- overflow;

and test whether high-regret weighting fails to prioritize hard capacity failure appropriately.

---

# 12. Agent B data discipline

The existing 24 held-out scenarios remain the final test set.

**Do not tune on them.**

Create:
- deterministic training scenario pools;
- preferably a separate validation scenario pool;
- preserve the original 24 held-out scenarios unchanged.

If no separate validation set is practical:
- run a predeclared grid;
- report the grid rather than selecting one "best" configuration as though independently validated.

No scenario may appear in both training and final held-out sets.

---

# 13. Agent B scenario families

Use the previously validated perturbation types:

- demand increases;
- capacity degradations;
- latency increases;
- moderate combined perturbations.

Do not use complete link removal in this fixed-route generalization study.

For larger \(S\), vary:
- affected demand/link;
- perturbation severity;
- perturbation type.

Avoid creating \(S=12\) from near-duplicates of one bottleneck.

---

# 14. Agent B correctness gates

## B0 — Reproduce original result
Before any ablation, exactly reproduce:
- original S=3 training set;
- original \(\eta,T,\rho=0\);
- route/weight trajectory;
- final adaptive route;
- published held-out metrics.

**STOP if this fails.**

## B1 — Weight-update correctness
For every iteration verify:

\[
\bar r_s=\operatorname{clip}(r_s,0,r_{\max})
\]

\[
\tilde w_s
=
\frac{w_se^{\eta\bar r_s}}
{\sum_jw_je^{\eta\bar r_j}}
\]

\[
w_s'=(1-\rho)\tilde w_s+\rho/S.
\]

Assertions:
- all weights finite;
- all positive;
- sum is 1;
- \(\eta=0\) produces no regret-driven change;
- larger regret gives larger pre-mixing boost;
- \(\rho\) pulls weights toward uniform;
- deterministic repeated run gives identical trajectory.

## B2 — Exact best-response correctness
At each outer iteration:
- exhaustively verify the chosen route minimizes the current weighted objective over the declared feasible domain;
- preserve all ties.

## B3 — Manifest integrity
Save hashes/IDs for:
- training scenarios;
- validation scenarios;
- held-out scenarios.

No leakage.

---

# 15. Agent B diagnostics

For each run record:

- \(S,\eta,T,\rho\);
- full route trajectory;
- full weight trajectory;
- training mean/worst regret;
- validation metrics if used;
- final held-out mean/worst regret;
- held-out survival rate;
- held-out overflow count/severity;
- nominal cost/performance.

Compute weight entropy:

\[
H(w)=-\sum_sw_s\log w_s
\]

and effective number of environments:

\[
\boxed{N_{\mathrm{eff}}=e^{H(w)}}.
\]

Interpretation:
- \(N_{\mathrm{eff}}\approx S\): pressure remains diverse;
- \(N_{\mathrm{eff}}\approx1\): strong specialization.

Test correlation between low \(N_{\mathrm{eff}}\) and poor held-out robustness.

---

# 16. Agent B experiment order

Avoid an unnecessarily huge full Cartesian product.

## B4 — Focused sweep first

Run:

\[
S\in\{3,5,8,12\}
\]

\[
\eta\in\{0,\ 0.25,\ 0.5,\ 1.0\}
\]

\[
T\in\{3,5\}
\]

with:

\[
\rho=0.
\]

## B5 — Diversity regularization

For representative/promising settings, test:

\[
\rho\in\{0.1,\ 0.25,\ 0.5\}.
\]

## B6 — Edge cases only if cheap

Optionally add:

\[
\eta=0.1,\ 2.0
\]

and:

\[
T=1,\ 10.
\]

Do not delay findings for edge cases.

---

# 17. Agent B required interpretation

Answer:

1. Does increasing \(S\) improve held-out survival/regret?
2. Does lower \(\eta\) improve generalization?
3. Does \(T\) matter after accounting for \(\eta\)?
4. Does weight collapse correlate with worse held-out performance?
5. Does \(\rho>0\) improve generalization?
6. Is static uniform (\(\eta=0\)) still best?
7. Is the hypothesis

\[
\text{strong selection + low diversity}
\rightarrow
\text{over-specialization}
\]

supported?

---

# 18. Agent B deliverables

Create:

```text
artifacts/evolution_ablation/
    manifests/
    runs/
    tables/
    figures/
```

Required:

```text
evolution_grid_results.csv
evolution_weight_trajectories.csv
evolution_scenario_manifests.json
EVOLUTION_ABLATION_FINDINGS.md
```

Recommended plots:

```text
01_survival_vs_eta.png
02_worst_regret_vs_eta.png
03_effective_environments_vs_generalization.png
04_training_S_vs_survival.png
05_eta_rho_heatmap.png
06_weight_trajectory_examples.png
```

---

# 19. Parent-session merge after both agents finish

Do **not** immediately combine implementations.

The parent Codex session should read both reports and create:

```text
HOLY_QOW_DUAL_TRACK_FINDINGS.md
```

It must summarize:

## Quantum track
- correctness of one-hot preservation;
- constrained-mixer resource overhead;
- comparison with uniform-valid sampling;
- repeatability.

## Evolution track
- cause of original held-out failure;
- effects of \(S,\eta,T,\rho\);
- evidence for/against over-specialization;
- best validated robustness policy.

Then output exactly one recommendation:

```text
COMBINED ADAPTIVE-CONSTRAINED QAOA: GO
```

or

```text
COMBINED ADAPTIVE-CONSTRAINED QAOA: NO-GO
```

or

```text
COMBINED ADAPTIVE-CONSTRAINED QAOA: CONDITIONAL GO
```

**Do not start the combined experiment without explicit user approval.**

---

# 20. Global correctness and evidence rules

Both agents must:

- preserve frozen tests;
- use shared validated evaluators;
- save raw artifacts before post-processing;
- never discard bad runs;
- never fabricate missing resource metrics;
- distinguish hypothesis from evidence;
- state when a result is negative or inconclusive.

A failed mixer or failed evolutionary hypothesis is a valid result.

---

# 21. Final instruction

> **Agent A isolates the quantum bottleneck using a one-hot-preserving QAOA under fixed uniform scenario weights. Agent B isolates the evolutionary/generalization mechanism using exact classical best responses and controlled ablations over scenario diversity and selection pressure. Each agent must verify its implementation against frozen references before interpreting results. Do not combine the two mechanisms. Report independently, then let the parent session decide whether a combined Holy QOW experiment is justified.**
