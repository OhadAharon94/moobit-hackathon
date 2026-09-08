# Holy QOW — Post-Stage-6A Evidence Handoff
## Authorized Work: Steps 0–2 Only

**Project:** Holy QOW — Robust Quantum Routing Across Changing Environments  
**Previous internal name:** Q-ERA  
**Status:** v1.1 Stages 0–5 complete; Stage 6A scalability study complete  
**Authorization boundary:** **Implement and run Steps 0–2 only. Report results. Do NOT start Step 3 until explicit user approval.**

---

# 1. Why this handoff exists

Stage 6A produced a useful but incomplete scaling picture.

The current evidence shows:

- deterministic \(D=4,5,6,8\) routing instances;
- verified QUBO scaling;
- Classiq synthesis through \(D=8\) / 24 logical qubits;
- real \(p=1\) QAOA runs at \(D=5\) and \(D=6\);
- encouraging but single-seed QAOA concentration relative to random bitstrings;
- very low one-hot and joint-feasible probability mass;
- strong random-valid-route performance because the valid search spaces are still small;
- no demonstrated quantum advantage.

The most important measured bottleneck is:

> The present \(|+angle\) initialization plus transverse-\(X\) mixer spends most probability outside the structurally valid one-hot routing subspace.

However, Stage 6A also suggests:

> **Conditioned on entering the one-hot routing subspace, QAOA may concentrate probability on useful routes better than uniform valid-route sampling.**

That observation is based on very few accepted samples and one optimizer seed, so it is not yet evidence.

Before implementing a new mixer or running a larger adaptive quantum experiment, answer three questions:

1. **Conditional quality:** Once QAOA reaches the valid routing subspace, is its distribution better than uniform valid sampling?
2. **Generalization / resilience:** Does adaptive Holy QOW routing produce plans that perform better under unseen network conditions?
3. **Repeatability:** Are the \(D=6\) QAOA observations reproducible across optimizer seeds, or were they seed-specific noise?

These are Steps 0, 1, and 2.

---

# 2. Hard authorization boundary

The agent is authorized to:

- implement Step 0;
- implement Step 1;
- implement and run Step 2;
- update tests and result schemas only as required for Steps 0–2;
- generate plots/tables/reports for Steps 0–2;
- report findings and recommend whether Step 3 is justified.

The agent is **NOT authorized** to begin:

- Step 3: adaptive Holy QOW at \(D=6\);
- Stage 6B: one-hot / XY / constraint-preserving mixer;
- \(p=2\);
- digital capacity alignment redesign;
- new quantum encodings;
- larger quantum execution beyond what Step 2 explicitly requires;
- substantive redesign of the frozen v1.1 / Stage 6A architecture.

After Steps 0–2, **STOP and report**.

Wait for explicit user approval before starting Step 3.

---

# 3. Frozen architecture

Treat all validated v1.1 and Stage 6A implementation definitions as frozen.

Do not change:

- one-hot path encoding;
- variable ordering;
- shared evaluator;
- scenario costs;
- normalization;
- QUBO convention;
- capacity postselection;
- regret definition;
- Classiq \(p=1\) ansatz;
- sample decoding;
- existing deterministic scaling instances;
- Stage 6A raw artifacts.

Do not overwrite existing runs.

All new work should produce new versioned artifacts.

---

# 4. Stage 6A evidence motivating the next work

Existing scaling results include:

| D | Method | One-hot mass | Joint-feasible mass | Best feasible objective gap | Near-optimal mass |
|---:|---|---:|---:|---:|---:|
| 4 | QAOA \(p=1\) | 5.225% | 2.344% | 0.00% | 0.049% |
| 5 | QAOA \(p=1\) | 0.586% | 0.195% | 0.40% | 0.024% |
| 6 | QAOA \(p=1\) | 0.610% | 0.195% | 3.23% | 0.024% |

The random-valid-route control allocates 100% of its samples to the one-hot subspace and recovered the exact optimum at the executed small sizes.

Therefore raw "best sample" comparison is not the right diagnostic.

The relevant question is whether the quantum distribution has useful **conditional concentration** after entering the route-valid subspace.

---

# 5. STEP 0 — Conditional-distribution analysis
## Priority: immediate; no new quantum jobs

## 5.1 Goal

Separate two possible bottlenecks:

1. **subspace access:** QAOA rarely reaches one-hot-valid states;
2. **conditional optimization quality:** even after reaching one-hot space, QAOA may or may not favor good routes.

This distinction is required before arguing that a constraint-preserving mixer is the natural next algorithmic improvement.

## 5.2 Required metrics

For every existing QAOA run at \(D=4,5,6\), compute:

\[
P(	ext{one-hot}),
\]

\[
P(	ext{joint feasible}),
\]

\[
P(	ext{near-optimal}),
\]

and:

\[
P(	ext{joint feasible}\mid 	ext{one-hot})
=
rac{P(	ext{joint feasible})}{P(	ext{one-hot})},
\]

\[
P(	ext{near-optimal}\mid 	ext{one-hot})
=
rac{P(	ext{near-optimal})}{P(	ext{one-hot})},
\]

when the denominator is nonzero.

Also compute where useful:

\[
P(	ext{near-optimal}\mid 	ext{joint feasible}).
\]

Preserve the Stage 6A near-optimal threshold unless an additional threshold is clearly labeled as secondary.

## 5.3 Factorization view

Explicitly report:

\[
P(	ext{near-optimal})
=
P(	ext{one-hot})
	imes
P(	ext{near-optimal}\mid	ext{one-hot}).
\]

This separates:

- probability of entering the meaningful routing space;
- quality of the distribution once inside it.

## 5.4 Fair random-valid comparison

Do **not** compare only against 4096 random-valid samples.

For each QAOA run:

1. let \(N_{	ext{1hot}}\) be the number of one-hot QAOA samples;
2. draw repeated uniform-random-valid batches of exactly \(N_{	ext{1hot}}\) routes;
3. for each random batch compute:
   - best objective gap;
   - near-optimal fraction;
   - joint-feasible fraction;
   - best regret;
4. compare the QAOA one-hot subset to the empirical matched-size random-valid distribution.

Use at least:

```text
1000 matched random-valid batches
```

No new quantum execution is required.

## 5.5 Required Step-0 plots

At minimum:

1. raw versus conditional probability:
   - \(P(	ext{one-hot})\)
   - \(P(	ext{joint feasible})\)
   - \(P(	ext{joint feasible}\mid	ext{one-hot})\)

2. conditional near-optimal concentration:
   - QAOA versus uniform valid sampling

3. matched-valid-sample control:
   - random-valid distribution of best objective gap for batches of size \(N_{	ext{1hot}}\)
   - QAOA result marked on the same plot

## 5.6 Interpretation rule

If QAOA is consistently better than matched random-valid sampling **conditional on one-hot validity**, the data supports:

> The current bottleneck is primarily reaching the valid one-hot subspace, rather than complete absence of useful QAOA concentration within it.

If not, report that clearly.

Do not force the constrained-mixer narrative if conditional QAOA quality is not better.

---

# 6. STEP 1 — Held-out resilience / generalization
## Priority: high value; classical evaluation only

## 6.1 Goal

Test whether the Holy QOW adaptive-routing concept generalizes beyond the environments used during optimization.

This is the clearest test of the biology-inspired thesis:

> A strong routing configuration should not merely fit the environments it was optimized against; it should remain effective under related unseen pressures.

## 6.2 Scope rule

For the main held-out study, do **not** use complete link removal.

A fixed routing configuration has no recourse if a selected path disappears.

Use unseen but compatible perturbations:

- demand increases;
- capacity degradations;
- latency increases;
- moderate combinations of demand and capacity changes.

Complete failure/recovery remains a separate future experiment.

## 6.3 Routes to evaluate

At minimum compare frozen routes representing:

1. nominal-only optimization;
2. static uniform multi-scenario optimization;
3. exact adaptive Holy QOW / exact-inner adaptive route;
4. QAOA adaptive Holy QOW route, if already available from the completed MVP;
5. exact pure minimax route as reference where useful.

Do not rerun quantum optimization for Step 1 unless an artifact required for comparison is genuinely missing.

## 6.4 Held-out scenario grid

Create a deterministic, predeclared scenario set not used in training.

Recommended components:

### Demand perturbations

For selected demands / groups:

\[
+10\%,\quad +20\%,\quad +30\%.
\]

### Capacity perturbations

On meaningful shared links:

\[
-10\%,\quad -20\%,\quad -30\%,\quad -40\%.
\]

### Latency perturbations

On selected bottleneck / alternate links:

\[
+10\%,\quad +25\%,\quad +50\%.
\]

### Combined perturbations

A small deterministic set, e.g.:

- moderate demand surge + moderate capacity degradation;
- regional demand increase + increased latency on an alternate corridor.

Target:

```text
10–30 held-out scenarios
```

Save the scenario manifest before comparative analysis.

## 6.5 Avoid test-set leakage

Do not tune after observing held-out results:

- route weights;
- scenario weights;
- \(lpha,eta\);
- training scenarios;
- selected route.

This is evaluation, not retraining.

## 6.6 Required metrics

For each route over held-out scenarios report:

- mean normalized cost;
- mean regret;
- worst-case regret;
- feasibility / survival rate;
- number / fraction of capacity-violating scenarios;
- mean overflow severity;
- maximum utilization;
- weighted latency.

If exact per-held-out-scenario optima are practical, use them for regret.

Otherwise use a clearly labeled best-known classical reference consistently.

## 6.7 Summary

Because these are deterministic stress cases rather than IID samples, do not overstate inferential statistics.

Report:

- mean;
- median;
- worst case;
- distribution / boxplot;
- number of scenarios won by each route.

## 6.8 Main question

Does adaptive routing improve unseen-scenario robustness relative to nominal-only and static uniform routing?

Strong evidence would be:

- lower worst-case regret;
- higher survival rate;
- fewer severe capacity violations;
- comparable nominal performance.

If adaptive and static robust routing are similar, report that honestly.

---

# 7. STEP 2 — D=6 QAOA repeatability
## Priority: mandatory before any D=6 adaptive quantum loop

## 7.1 Goal

Determine whether the encouraging single-seed D=6 Stage 6A result is reproducible.

Stage 6A used one optimizer seed and produced only 8 jointly feasible samples out of 4096.

That is insufficient for a statistical claim.

## 7.2 Number of runs

Preferred:

\[
5	ext{ independent optimizer seeds at }D=6.
\]

Minimum if constrained:

\[
3	ext{ seeds}.
\]

Do not expand to 10 until 5 are complete and submission time remains safe.

D=5 repeats are optional only after D=6 is complete.

## 7.3 Freeze configuration

Apart from optimizer seed, preserve the Stage 6A D=6 static QAOA setup:

- same deterministic instance;
- same uniform scenario weights;
- same \(p=1\);
- same optimizer;
- same iteration cap;
- same optimizer shots;
- same final readout shots;
- same energy mode;
- same \(M\);
- same postselection;
- same near-optimal threshold.

If a setting must change due to platform limitations, document it and do not silently combine incomparable runs.

## 7.4 Required per-seed metrics

For every seed:

- optimizer seed;
- optimizer trace;
- one-hot count and mass;
- jointly feasible count and mass;
- near-optimal count and mass;
- \(P(	ext{joint feasible}\mid	ext{one-hot})\);
- \(P(	ext{near-optimal}\mid	ext{one-hot})\);
- best feasible objective gap;
- best feasible worst-case regret;
- probability mass on the exact/best-known optimum if sampled;
- runtime;
- circuit resources;
- warnings / execution status.

## 7.5 Uncertainty reporting

Do not simply pool all samples.

Report variation **across optimizer seeds** using:

- mean;
- median;
- min/max;
- IQR where useful.

For within-run proportions, Wilson/binomial intervals may be reported.

Clearly distinguish:

1. shot uncertainty within a fixed optimized circuit;
2. optimizer-seed variability between independently optimized circuits.

## 7.6 Matched controls

For every QAOA seed:

### Random bitstrings
Use the same final readout sample count.

### Random valid routes
Use both:

1. the same total sample count as QAOA;
2. matched-size batches using exactly the number of one-hot QAOA samples.

These answer different questions:

- random bitstrings test access to useful binary states;
- matched random valid routes test concentration once inside the valid subspace.

## 7.7 Success criterion

Do **not** require QAOA to beat strong classical optimization.

A meaningful repeated result exists if D=6 QAOA shows one or more of:

- reproducibly larger one-hot mass than random bitstrings;
- reproducibly larger feasible mass than random bitstrings;
- conditional near-optimal concentration above matched random-valid sampling;
- consistently smaller best-feasible objective gap than random-bit controls.

If none is reproducible, conclude that Stage 6A's encouraging single-seed result was seed-sensitive.

That is still valid evidence.

---

# 8. Why Step 3 is gated

Step 3 would run the **adaptive Holy QOW outer loop at D=6**.

This should happen only if Step 2 shows that the D=6 static QAOA solve is sufficiently stable to serve as an inner best response.

Otherwise the adaptive outer loop could amplify:

- low accepted-sample counts;
- optimizer noise;
- seed instability.

Therefore:

\[
oxed{	ext{Step 3 must not start automatically.}}
\]

After Steps 0–2:

1. stop new implementation/execution;
2. write the consolidated report;
3. issue a GO / NO-GO / CONDITIONAL GO recommendation for Step 3;
4. wait for explicit user approval.

---

# 9. Required report after Steps 0–2

Create:

```text
POST_6A_STEPS_0_2_FINDINGS.md
```

It must answer:

## Step 0
- How much of QAOA's weakness is due to failure to enter one-hot space?
- Conditional on one-hot validity, is QAOA better than matched uniform-valid sampling?
- Are the existing D=5/D=6 observations meaningful after fair sample-budget matching?

## Step 1
- Does adaptive Holy QOW routing generalize to unseen network conditions?
- Which route has the lowest held-out worst-case regret?
- Which has the highest survival rate?
- Is adaptive routing materially better than static multi-scenario routing?

## Step 2
- Is D=6 behavior reproducible across seeds?
- What is the seed-level distribution of one-hot and feasible probability?
- What is the conditional near-optimal concentration?
- Is QAOA consistently better than random-bit and matched random-valid controls?
- Are Stage 6A conclusions strengthened, weakened, or overturned?

## Recommendation

End with exactly one of:

```text
STEP 3 RECOMMENDATION: GO
```

```text
STEP 3 RECOMMENDATION: NO-GO
```

or

```text
STEP 3 RECOMMENDATION: CONDITIONAL GO
```

Explain the reason.

**Do not begin Step 3.**

---

# 10. Required artifacts

Use a new artifact area such as:

```text
artifacts/post6a/
    conditional/
    heldout/
    repeatability/
    tables/
    figures/
```

Recommended summary tables:

```text
conditional_metrics.csv
matched_valid_control.csv
heldout_scenarios.csv
heldout_route_results.csv
d6_repeatability.csv
d6_seed_level_summary.csv
```

Recommended figures:

```text
01_raw_vs_conditional_probability.png
02_matched_valid_quality.png
03_heldout_regret_distribution.png
04_heldout_survival.png
05_d6_seed_repeatability.png
06_d6_conditional_quality_by_seed.png
```

All figures must regenerate from saved tables without Classiq access.

---

# 11. Execution order

```text
STEP 0
existing Stage 6A artifacts only
    |
    v
conditional metrics + matched valid controls
    |
    v
STEP 1
freeze held-out scenario manifest
    |
    v
evaluate frozen routes
    |
    v
STEP 2
D=6 repeated QAOA seeds
    |
    v
matched controls + uncertainty summary
    |
    v
CONSOLIDATED REPORT
    |
    v
STOP
    |
    v
WAIT FOR USER APPROVAL FOR STEP 3
```

Step 1 preparation may run in parallel with Step 2 only if it does not create code conflicts.

Do not skip Step 0 interpretation.

---

# 12. Sanity-check gates

## Gate 0A — artifact consistency

Before Step 0:

- existing Stage 6A tables reproduce the published summary values;
- counts equal recorded shot budgets;
- denominators are nonzero where conditional values are reported.

If not: STOP and report the discrepancy.

## Gate 0B — matched random-valid fairness

Matched random-valid batches must contain exactly the same number of valid-route samples as the corresponding one-hot QAOA subset.

Do not use 4096 random-valid samples as the only conditional-quality comparison against ~20–30 QAOA valid samples.

## Gate 1A — held-out freeze

Save the complete held-out scenario manifest before generating comparative route results.

## Gate 1B — evaluator reuse

Held-out evaluation must use the validated core evaluator.

Do not duplicate cost/load/feasibility formulas in a notebook.

## Gate 2A — configuration reproduction

Before launching all seeds, verify one D=6 run uses the same configuration/schema as Stage 6A.

## Gate 2B — no silent seed selection

Record failed and poor seeds.

One logged technical retry is acceptable.

Do not discard unattractive runs.

---

# 13. Interpretation boundaries

## Allowed only if supported

> QAOA's primary current weakness is low probability of entering the structurally valid routing subspace.

> Conditional on entering the valid route space, QAOA concentrates more probability on high-quality routes than uniform valid sampling.

> Adaptive multi-environment training improves held-out resilience.

> D=6 quantum behavior is reproducible across optimizer seeds.

Use each statement only if the new evidence supports it.

## Not allowed

- "The quantum algorithm scales."
- "Constraint-preserving QAOA will solve the problem."
- "Holy QOW beats classical optimization."
- "We demonstrated quantum advantage."
- "Evolution guarantees generalization."
- "The D=6 single-seed result proves superiority."

---

# 14. Step 3 — NOT AUTHORIZED

If later approved, Step 3 will compare at D=6:

1. static uniform-weight QAOA;
2. exact-inner adaptive Holy QOW;
3. QAOA-inner adaptive Holy QOW.

The static and adaptive quantum methods must use matched total quantum optimization/readout budgets.

This step is intentionally postponed until Steps 0–2 establish that the D=6 quantum inner solve is stable enough.

---

# 15. Final instruction

> **Implement and run Steps 0–2 only, in order. The purpose is to determine whether the current QAOA distribution has useful conditional concentration, whether Holy QOW's adaptive robustness generalizes to unseen scenarios, and whether the D=6 quantum observations are repeatable. Preserve all frozen v1.1 and Stage 6A definitions. Do not implement Step 3 or a constraint-preserving mixer. After Steps 0–2, create the required consolidated findings report, give a GO/NO-GO recommendation for Step 3, and stop for user approval.**
