# Holy QOW — Post-Stage-6A Steps 0–2 Findings

## Executive conclusion

Steps 0–2 are complete. The results identify one-hot subspace access as the largest multiplicative loss in the current generic-mixer QAOA, but they do **not** establish better optimization after conditioning on valid routing states. The held-out test also does not support the claim that the current adaptive route generalizes better than the static multi-scenario route.

The D=6 repeats contain a real positive signal against uninformed random bitstrings: QAOA found a lower best feasible objective gap and lower best feasible worst-case regret in all five paired runs. However, one-hot and feasible masses varied strongly by optimizer seed, one run produced only one feasible sample, no run sampled the exact optimum, and none of the fair matched-valid comparisons was significant.

**Overall assessment of the previous Stage 6A interpretation: WEAKENED, not overturned.** The random-bit advantage is strengthened, while the more important suggestion of useful conditional concentration is weakened.

## Scope and verification

- Authorization was limited to Steps 0–2. No adaptive D=6 quantum loop, constraint-preserving mixer, p=2 circuit, new encoding, or capacity redesign was implemented.
- Gate 0A passed: the frozen D=4, D=5, and D=6 raw distributions each decode to 4,096 shots, and every comparable recorded summary field reproduces within the declared tolerance. The legacy D=4 summary did not record the best-regret field; that newly computed field was marked `NOT_RECORDED`, not treated as a mismatch.
- Gate 0B passed: every matched random-valid batch has exactly the same size as the corresponding QAOA one-hot subset.
- Gate 1A passed: the 24-scenario held-out manifest and five-route manifest were hash-frozen before route comparison.
- Gate 1B passed: held-out evaluation reused `qera_scaling.evaluate.ScalingEvaluator` rather than duplicating cost or feasibility formulas.
- Gate 2A passed: the existing 18-qubit D=6 qprog and synthesis manifest are hash-bound to the frozen objective and configuration. Only optimizer seed changed.
- Gate 2B passed: the original seed and all four new seeds are retained, including the poor seed 6202.
- Tests: frozen v1.1 `62 passed`; frozen Stage 6A `31 passed`; post-6A `9 passed`.

Primary verification record: [`artifacts/post6a/baseline_verification.json`](artifacts/post6a/baseline_verification.json).

## Step 0 — Conditional-distribution analysis

The preserved near-optimal definition is a jointly feasible route within an absolute objective gap of 0.01.

| D | One-hot | Joint feasible | Near-optimal | P(feasible \| one-hot) | P(near-optimal \| one-hot) | QAOA one-hot samples |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 5.225% | 2.344% | 0.0488% | 44.86% | 0.935% | 214 |
| 5 | 0.586% | 0.195% | 0.0244% | 33.33% | 4.167% | 24 |
| 6 | 0.610% | 0.195% | 0.0244% | 32.00% | 4.000% | 25 |

The factorization is exact up to floating-point rounding:

\[
P(\text{near-optimal}) = P(\text{one-hot})P(\text{near-optimal}\mid\text{one-hot}).
\]

For D=6, for example, \(0.0061035 \times 0.04 = 0.0002441\). Thus the low one-hot probability suppresses the observed near-optimal probability by a factor of about 164 relative to the measured conditional distribution. This diagnoses the principal bottleneck; it does **not** prove that a different mixer will preserve or improve the conditional distribution.

### Matched-valid comparison

Each QAOA one-hot subset was compared with 1,000 uniform-random-valid batches of the same size.

| D | N | p(random best gap ≤ QAOA) | p(random best regret ≤ QAOA) | p(random feasible fraction ≥ QAOA) | p(random near fraction ≥ QAOA) |
|---:|---:|---:|---:|---:|---:|
| 4 | 214 | 0.920 | 0.996 | 0.857 | 0.729 |
| 5 | 24 | 0.193 | 0.193 | 0.443 | 0.329 |
| 6 | 25 | 0.223 | 0.205 | 0.297 | 0.316 |

None is significant at 0.05. The D=5 and D=6 QAOA subsets look encouraging in some point estimates, but the fair batch-size comparison shows that samples this good occur often under uniform valid sampling. Therefore:

- most raw-probability loss is caused by failing to enter the one-hot subspace;
- once inside that subspace, useful QAOA concentration is **not established**;
- the original D=5/D=6 accepted-sample observation is meaningful as a hypothesis, not as evidence of conditional superiority.

Evidence: [`conditional_metrics.csv`](artifacts/post6a/conditional/conditional_metrics.csv), [`matched_valid_summary.csv`](artifacts/post6a/conditional/matched_valid_summary.csv), and [`01_raw_vs_conditional_probability.png`](artifacts/post6a/figures/01_raw_vs_conditional_probability.png).

## Step 1 — Held-out resilience and generalization

The held-out set contains 24 predeclared scenarios: six each for demand, capacity, latency, and combined perturbations. It contains no full link removal. Every scenario admits at least one feasible fixed route, and no route or weight was tuned after evaluation.

| Frozen route | Assignment | Mean regret | Worst regret | Survival | Violations | Max overflow | Mean latency |
|---|---|---:|---:|---:|---:|---:|---:|
| Nominal-only representative | (0,1,1,0) | 0.0247 | **0.2347** | 20/24 (83.3%) | 4 | 0.4 | 30.28 |
| Static uniform multi-scenario | (1,0,2,2) | 0.0754 | 0.3163 | **24/24 (100%)** | **0** | **0.0** | 36.14 |
| Exact adaptive | (0,1,1,2) | 0.1470 | 0.4783 | 22/24 (91.7%) | 2 | 0.4 | 33.91 |
| QAOA adaptive | (0,1,1,2) | 0.1470 | 0.4783 | 22/24 (91.7%) | 2 | 0.4 | 33.91 |
| Exact minimax | (0,1,1,2) | 0.1470 | 0.4783 | 22/24 (91.7%) | 2 | 0.4 | 33.91 |

The nominal-only row is one deterministic representative of a tied nominal optimum, so its apparent regret lead should not be generalized to every nominal optimum. The exact-adaptive, saved-QAOA-adaptive, and minimax labels all resolve to the same assignment; their identical held-out results are not independent confirmations.

Answers to the Step 1 questions:

- **Does adaptive Holy QOW generalize?** It improves survival over this nominal representative (22/24 versus 20/24), but it has much worse mean and worst-case regret and does not match the static route's complete survival. The planned biological generalization hypothesis is not supported by this test.
- **Lowest held-out worst-case regret:** the nominal-only representative, 0.2347.
- **Highest survival:** static uniform multi-scenario, 24/24 with no overflow.
- **Adaptive versus static:** adaptive is materially worse here: 91.7% versus 100% survival, 0.4783 versus 0.3163 worst regret, and 0.1470 versus 0.0754 mean regret.

These are deterministic stress-test comparisons, not IID statistical estimates.

Evidence: [`heldout_scenario_manifest.json`](artifacts/post6a/heldout/heldout_scenario_manifest.json), [`heldout_route_results.csv`](artifacts/post6a/heldout/heldout_route_results.csv), and [`03_heldout_regret_distribution.png`](artifacts/post6a/figures/03_heldout_regret_distribution.png).

## Step 2 — D=6 QAOA repeatability

Five independent optimizer seeds were evaluated: the frozen original 6106 plus new seeds 6201–6204. Every seed used the same Classiq p=1 program, 10 optimizer iterations, 512 optimizer shots, 4,096 final shots, uniform weights, base energy, one-hot penalty, and starting parameters. All five runs completed; no seed was discarded.

The frozen circuit has 18 qubits, depth 138, 294 gates, and 160 two-qubit gates. Recorded runtimes ranged from 10.79 to 21.98 seconds.

| Seed | One-hot count | Feasible count | Near-opt count | P(one-hot) | P(feasible) | P(feasible \| one-hot) | P(near \| one-hot) | Best objective gap | Best worst regret |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6106 | 25 | 8 | 1 | 0.610% | 0.195% | 32.0% | 4.00% | 0.00836 | 0.19883 |
| 6201 | 48 | 11 | 1 | 1.172% | 0.269% | 22.9% | 2.08% | 0.00216 | 0.18405 |
| 6202 | 5 | 1 | 0 | 0.122% | 0.024% | 20.0% | 0.00% | 0.04863 | 0.36349 |
| 6203 | 63 | 14 | 1 | 1.538% | 0.342% | 22.2% | 1.59% | 0.00352 | 0.19556 |
| 6204 | 18 | 6 | 0 | 0.439% | 0.146% | 33.3% | 0.00% | 0.03601 | 0.31118 |

No QAOA seed sampled the exact joint optimum. Only three near-optimal shots were observed across the five runs.

### Optimizer-seed variability

These statistics are over five seed-level point estimates, not pooled shots:

| Metric | Mean | Sample SD | Median | Range |
|---|---:|---:|---:|---:|
| P(one-hot) | 0.776% | 0.571 percentage points | 0.610% | 0.122–1.538% |
| P(joint feasible) | 0.195% | 0.121 percentage points | 0.195% | 0.024–0.342% |
| P(feasible \| one-hot) | 26.09% | 6.11 percentage points | 22.92% | 20.00–33.33% |
| P(near \| one-hot) | 1.534% | 1.665 percentage points | 1.587% | 0–4.00% |
| Best objective gap | 0.01973 | 0.02122 | 0.00836 | 0.00216–0.04863 |
| Best worst-case regret | 0.25062 | 0.08147 | 0.19883 | 0.18405–0.36349 |

Per-seed 95% Wilson intervals are stored separately in `d6_repeatability.csv`. They capture finite-shot uncertainty for a fixed optimized circuit; the table above captures variability between optimized circuits.

### Controls

- Mean QAOA one-hot probability was 0.776%, versus 0.239% for paired random bitstrings: a 3.24× ratio. QAOA was higher in 4/5 pairs; the one-sided sign-test p-value is 0.1875.
- Mean QAOA joint-feasible probability was 0.195%, versus 0.0537% for random bitstrings: a 3.64× ratio. QAOA was higher in 4/5 pairs; p=0.1875.
- QAOA found a smaller best feasible objective gap and a smaller best feasible worst-case regret than its random-bit control in all 5/5 pairs. The discrete one-sided sign-test p-value is 0.03125 for each. This is the clearest repeated positive result.
- Against 4,096 random-valid routes, QAOA's mean conditional feasibility was 26.09% versus 26.36%, and mean conditional near-optimal concentration was 1.534% versus 1.650%.
- Against 1,000 random-valid batches matched to each seed's actual one-hot count (5–63), **zero of five seeds** achieved p<0.05 for best gap, best regret, feasible fraction, or near-optimal fraction. The best-gap empirical p-values were 0.230, 0.238, 0.537, 0.405, and 0.690.

The D=6 behavior therefore has a reproducible advantage over uninformed random-bit sampling in the quality of the best feasible sample, but it is not a stable inner best-response oracle. The raw access probabilities vary by more than an order of magnitude, and conditional performance is indistinguishable from uniform valid sampling at the available accepted counts.

Evidence: [`d6_repeatability.csv`](artifacts/post6a/repeatability/d6_repeatability.csv), [`d6_seed_level_summary.csv`](artifacts/post6a/repeatability/d6_seed_level_summary.csv), [`d6_control_comparison_summary.json`](artifacts/post6a/repeatability/d6_control_comparison_summary.json), [`optimizer_traces.csv`](artifacts/post6a/repeatability/optimizer_traces.csv), and [`05_d6_seed_repeatability.png`](artifacts/post6a/figures/05_d6_seed_repeatability.png).

## Reproduction without new quantum jobs

From the `implementation` directory, the saved evidence can be reprocessed with:

```powershell
..\.venv-classiq\Scripts\python.exe post6a\scripts\verify_frozen_baseline.py
..\.venv-classiq\Scripts\python.exe post6a\scripts\run_step0_conditional.py
..\.venv-classiq\Scripts\python.exe post6a\scripts\run_step1_heldout.py
..\.venv-classiq\Scripts\python.exe post6a\scripts\process_step2_repeatability.py
$env:MPLCONFIGDIR = "$PWD\artifacts\post6a\.mplconfig"
..\.venv-classiq\Scripts\python.exe post6a\scripts\generate_post6a_plots.py
..\.venv-classiq\Scripts\python.exe -m pytest tests -q
..\.venv-classiq\Scripts\python.exe -m pytest stage6a\tests -q
..\.venv-classiq\Scripts\python.exe -m pytest post6a\tests -q
```

No Classiq access is needed for those commands. The new quantum raw results and optimizer traces are already saved under `artifacts/post6a/repeatability/runs/`.

The same workflow is organized as a top-to-bottom, analysis-only notebook at [`notebooks/holy_qow_post6a_steps_0_2.ipynb`](notebooks/holy_qow_post6a_steps_0_2.ipynb). Its executed validation copy completed 21 cells with zero errors and is saved at [`artifacts/post6a/notebook_validation.ipynb`](artifacts/post6a/notebook_validation.ipynb).

## Recommendation rationale

Step 3 would repeatedly use D=6 QAOA as an inner best-response solver. The present solver is not reliable enough for that role: one accepted-feasible count fell to 1/4,096, conditional quality showed no significant advantage, and the held-out study did not validate an adaptive-route resilience benefit. Running the adaptive outer loop now would risk amplifying optimizer-seed and finite-shot noise without answering the current scientific weaknesses.

The positive 5/5 comparison against random bitstrings is worth preserving as evidence, but it does not clear the stronger stability gate required for Step 3.

STEP 3 RECOMMENDATION: NO-GO
