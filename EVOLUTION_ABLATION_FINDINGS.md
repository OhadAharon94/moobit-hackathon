# Holy QOW Evolution / Generalization Ablation Findings

## Scope and status

Track B is complete. This study used only the exact exhaustive classical inner solver. It did not call Classiq, run QAOA, use the constraint-preserving mixer, or consume Agent A's implementation.

All frozen v1.1, Stage 6A, and Post-6A source and evidence were preserved. The new evidence is isolated under `artifacts/evolution_ablation/`.

## Correctness gates

### B0 — frozen reproduction: PASS

Before the ablation, the original S=3, η=1, T=3, ρ=0 cost-adaptive run reproduced the frozen route, scenario-weight, regret, and objective trajectory to absolute tolerance `1e-12`:

| Iteration | Route | Scenario weights (nominal, surge, degradation) |
|---:|---|---|
| 0 | `(1,0,2,2)` | `(0.333333, 0.333333, 0.333333)` |
| 1 | `(1,0,2,2)` | `(0.302057, 0.290537, 0.407406)` |
| 2 | `(0,1,1,2)` | `(0.267068, 0.247085, 0.485847)` |

The final route also reproduced every published Post-6A held-out summary field, including survival `0.916667`, worst regret `0.478334`, two violating scenarios, and maximum overflow `0.4`.

Evidence: `artifacts/evolution_ablation/manifests/b0_reproduction.json`.

### B1 — weight update: PASS

Every update was independently recomputed from the declared clipped-regret formula. The audit verified:

- clipping to `[0,1]`;
- strict positivity and normalization;
- η=0 identity behavior;
- monotonic pre-mixing boost with regret;
- exact ρ contraction toward uniform;
- deterministic replay.

Evidence: `artifacts/evolution_ablation/manifests/weight_update_correctness.json`.

### B2 — exact best response: PASS

At every outer iteration of all 192 runs, all 81 structurally valid routes were rescored over the jointly training-feasible domain. The selected route equals the first deterministic member of the complete minimum-energy tie set. No tie was discarded from the raw record.

### B3 — scenario integrity: PASS

The study froze:

- a nested 12-scenario training pool, with the original three environments as its S=3 prefix;
- a separate 16-scenario validation pool;
- the unchanged 24-scenario Post-6A final test.

Training, validation, and final pools have pairwise-disjoint IDs and parameter fingerprints. No scenario removes a link, every individual scenario has a feasible route, and each S=3/5/8/12 training prefix has a nonempty jointly feasible domain.

The scenario-manifest SHA-256 is `f32a3d38ab74f2b17433df9fb5c26e84b49de105473381ee54063b9fb5cbfe1c`. The predeclared 192-run grid SHA-256 is `ad3e96d0ac4b95e6cac74b17ce305d1c17c40c2bc784b17c75c9e49fa61e6a95`.

## Experiment design

The frozen grid contains:

- 32 focused B4 runs over `S ∈ {3,5,8,12}`, `η ∈ {0,0.25,0.5,1}`, `T ∈ {3,5}`, `ρ=0`;
- 72 matched B5 diversity-mixing runs with `ρ ∈ {0.1,0.25,0.5}`;
- 88 cheap B6 edge cases covering `η ∈ {0.1,2}` and `T ∈ {1,2,10}` in addition to the focused values.

Policy selection was performed using validation survival, overflow, worst regret, mean regret, and nominal cost, in that order. The selection record was hash-bound before final-test evaluation.

The predeclared `η>0` eligibility rule admitted `T=1`, although `T=1` performs no update. That original record was retained. A transparent validation-only supplement therefore also reports the best genuinely adaptive run with `η>0` and `T>1`; it did not use final-test columns.

## Central comparison

| Policy | S, η, T, ρ | Route | Validation survival / worst regret | Final survival / worst regret | Final mean regret |
|---|---|---|---|---|---:|
| Original static uniform | 3, 0, 3, 0 | `(1,0,2,2)` | `1.0 / 0.191211` | `1.0 / 0.316311` | `0.075445` |
| Original adaptive | 3, 1, 3, 0 | `(0,1,1,2)` | `1.0 / 0.293457` | `0.916667 / 0.478334` | `0.146990` |
| Validation-selected static | 8, 0, 1, 0 | `(0,2,1,2)` | `1.0 / 0.158819` | `1.0 / 0.316311` | `0.080240` |
| Validation-selected genuine adaptive | 8, 0.1, 2, 0 | `(0,2,1,2)` | `1.0 / 0.158819` | `1.0 / 0.316311` | `0.080240` |

The validation-selected genuinely adaptive policy is exactly tied with validation-selected static uniform weighting because its small update does not change the exact best response. It does not beat static weighting. The original S=3 static policy retains the lowest final mean regret among these robust policies.

## Hypothesis results

### 1. Does increasing S improve held-out survival or regret?

It removes the observed low-diversity failure mode, but does not establish an advantage over static uniform weighting.

In the focused B4 sweep:

| S | Mean final survival | Mean final worst regret | Distinct routes |
|---:|---:|---:|---:|
| 3 | `0.968750` | `0.377070` | 2 |
| 5 | `1.000000` | `0.316311` | 1 |
| 8 | `1.000000` | `0.316311` | 1 |
| 12 | `1.000000` | `0.316311` | 1 |

S=5 stabilizes the original static route across all focused η/T values. S=8 and S=12 stabilize a different feasible route. Increasing S beyond five does not reduce final worst regret below the static S=3 baseline.

### 2. Does lower η improve generalization?

Yes, in the low-diversity regime. Across the focused sweep:

| η | Mean final survival | Mean final worst regret |
|---:|---:|---:|
| 0 | `1.000000` | `0.316311` |
| 0.25 | `1.000000` | `0.316311` |
| 0.5 | `0.989583` | `0.336564` |
| 1.0 | `0.979167` | `0.356817` |

The deterioration comes from S=3. At S≥5, the focused runs are insensitive to η because they retain a robust exact best response.

### 3. Does T matter after accounting for η?

T is an exposure multiplier, not an independent source of improvement. In the focused grid, T=3 averaged survival `0.994792` and worst regret `0.326438`; T=5 averaged `0.989583` and `0.336564`.

The route boundary is crossed earlier when η is larger: at S=3, η=1 switches by T=3, whereas η=0.5 switches by T=5. The η=2 edge cases also show non-monotonic route cycling at longer T. More iterations therefore do not reliably improve robustness.

### 4. Does weight collapse correlate with worse robustness?

Weight concentration is associated with worse outcomes, but severe collapse does not explain the original failure.

Across the 152 runs with η>0 and T>1, using concentration `1 − N_eff/S`:

- Pearson correlation with final worst regret: `0.402`;
- Spearman correlation with final worst regret: `0.443`;
- Pearson correlation with final survival: `−0.402`;
- within-S Pearson correlations with final worst regret: `0.517` to `0.884`.

However, the original failing run has `N_eff=2.854` out of 3, an effective fraction of `0.951`, and maximum weight `0.486`. This is modest concentration, not collapse toward one environment. It was still sufficient to cross a discontinuous exact-best-response boundary.

### 5. Does ρ>0 improve generalization?

It prevents harmful switches, but does not create a policy better than static uniform weighting.

In 72 matched comparisons, ρ changed the final route in 7 cases. All seven improved validation and final worst regret, none worsened it, and each recovered the static-quality route `(1,0,2,2)`. For those cases, final survival increased by `0.083333` and worst regret improved by `0.162023`.

Across matched B5 settings:

| ρ | Mean final survival | Mean final worst regret | Mean N_eff/S |
|---:|---:|---:|---:|
| 0 | `0.989583` | `0.336564` | `0.973027` |
| 0.1 | `0.996528` | `0.323062` | `0.981368` |
| 0.25 | `0.996528` | `0.323062` | `0.989839` |
| 0.5 | `1.000000` | `0.316311` | `0.997538` |

Thus ρ acts as an effective safety regularizer against adaptation damage.

### 6. Is static uniform weighting still best?

Yes. No validation-selected adaptive policy beats its static comparator on the final test. The best genuine adaptive policy ties the validation-selected static policy exactly, and the original S=3 static route has slightly better final mean regret (`0.075445` versus `0.080240`) with the same survival and worst regret.

### 7. Is “strong selection + low diversity → over-specialization” supported?

Supported in a qualified form.

- Stronger η, more update opportunities, and S=3 cause the exact response to specialize to a route that generalizes poorly.
- Increasing S to five or applying diversity mixing prevents that switch.
- Lower `N_eff/S` correlates with worse generalization.

But the strict “weight collapse” version is not supported: the original weights remain fairly diverse. The mechanism is better described as **modest low-diversity weight concentration crossing a discontinuous best-response boundary**, not convergence to a single environment.

## Regret/feasibility mismatch

This residual hypothesis is supported as a diagnosis, not proven causally because the fitness function was deliberately left unchanged.

All exact responses are constrained to be feasible on their training environments, so training overflow is always zero and supplies no gradient. Multiplicative weights react only to normalized regret. In the original trajectory, the single U-M1 degradation receives weight `0.486`, but that localized pressure does not represent other demand/capacity combinations. The resulting route remains training-feasible yet fails 2 of 24 unseen cases with maximum overflow `0.4`.

More diverse scenarios and ρ reduce the failure, but neither produces an adaptive advantage. This suggests that the remaining limitation is not only selection strength; it is also the mismatch between regret-driven reweighting over a tiny fixed environment set and operational failure under unseen capacity patterns.

## What Track B establishes independently

1. The original generalization failure is real and exactly reproducible without quantum sampling.
2. It is a classical outer-loop phenomenon caused by the interaction of low S, selection exposure η/T, and a discrete best-response boundary.
3. Severe environmental-weight collapse is not necessary and did not occur in the original run.
4. Larger S and ρ are effective safeguards against harm.
5. Within this frozen routing model, adaptation did not outperform a well-chosen static uniform multi-environment solution.

## Limitations

- D=4 has only 81 structurally valid routes and produces discrete, tied outcomes; correlation estimates contain many duplicate routes.
- Scenario pools are deterministic and diverse but remain synthetic perturbations of one topology.
- Validation selection favored S=8 while the final mean regret slightly favored the original S=3 static route, illustrating finite scenario-pool mismatch.
- The study did not change the regret signal, feasibility handling, route-recourse model, or combine this track with any quantum ansatz.
- The supplemental T>1 adaptive eligibility rule was added transparently after the predeclared η>0 rule exposed a semantic T=1 degeneracy; it used validation fields only.

## Evidence index

- `artifacts/evolution_ablation/manifests/evolution_scenario_manifests.json`
- `artifacts/evolution_ablation/manifests/predeclared_experiment_grid.json`
- `artifacts/evolution_ablation/manifests/selection_before_final.json`
- `artifacts/evolution_ablation/tables/evolution_grid_results.csv`
- `artifacts/evolution_ablation/tables/evolution_weight_trajectories.csv`
- `artifacts/evolution_ablation/tables/evolution_policy_comparison.csv`
- `artifacts/evolution_ablation/tables/evolution_diagnostics.json`
- `artifacts/evolution_ablation/figures/`

## Independent Track B recommendation

Do not claim an evolutionary/generalization advantage and do not use unregularized S=3 adaptation in a combined experiment. If the parent later authorizes a combined study for diagnostic purposes, require at least S=5 and either small η or explicit diversity mixing, with static uniform weighting retained as the primary comparator. Track B alone provides no evidence that adaptation will improve constrained QAOA.
