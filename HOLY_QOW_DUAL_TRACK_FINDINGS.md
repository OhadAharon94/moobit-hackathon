# Holy QOW Dual-Track Findings

**Date:** 9 September 2026  
**Integration branch:** `dual-track-coordination`  
**Track A branch:** `stage6b-constraint-mixer`  
**Track B branch:** `evolution-ablation`

## Executive conclusion

Both independent tracks completed their authorized work and preserved all frozen v1.1, Stage 6A, and Post-6A evidence.

The Stage 6B constrained mixer is mathematically and empirically correct at D=4. It removes the dominant X-mixer failure mode by keeping essentially all probability in the one-hot routing subspace. However, after that structural correction, p=1 constrained QAOA did not reproducibly improve the meaningful solution-quality distribution relative to matched uniform-random-valid routing. It also roughly doubled the gate and two-qubit-gate counts. The predeclared D=6 gate therefore failed, and no D=6 constrained-QAOA job was attempted.

The evolution ablation explains the earlier adaptive generalization failure as a small-training-set and excessive-selection-pressure effect acting through a discontinuous exact best response. Scenario-weight concentration correlates with worse held-out robustness, but the original run did not undergo extreme weight collapse. Increasing environmental diversity, reducing selection strength, limiting repeated exposure, or mixing weights back toward uniform can prevent the harmful route switch. The moderated policies recovered static performance, but none beat the validation-selected static uniform policy on the final held-out set.

The combined adaptive plus constrained-QAOA algorithm is therefore not justified by the current evidence. Combining two individually non-superior mechanisms would increase complexity without an empirical basis for expecting a benefit.

## Scope, isolation, and verification

The tracks were developed in separate branches and worktrees. Track A used fixed uniform scenario weights and did not consume Track B's new implementation. Track B used the exact classical inner solver only and ran no quantum jobs. Their commits touched no common paths before integration.

The parent integration reran every relevant test suite after both branches were merged:

| Suite | Result |
|---|---:|
| Frozen v1.1 | 62 passed |
| Frozen Stage 6A | 31 passed |
| Frozen Post-6A | 9 passed |
| Stage 6B constrained mixer | 20 passed |
| Evolution ablation | 10 passed |
| **Total** | **132 passed, 0 failed** |

Raw samples, optimizer traces, manifests, hashes, failed/negative outcomes, exact tables, and figures were retained under `artifacts/stage6b/` and `artifacts/evolution_ablation/`.

## Track A — one-hot-preserving QAOA

### Correctness result

The constrained construction uses a Dicke/W initial state for each three-route demand and an exchange mixer implemented by pairwise `RXX(2 beta)` and `RYY(2 beta)` operations. The tested mixer preserves Hamming weight one within each demand register.

All D=4 correctness gates passed:

- The single-demand preparation was uniform over `001`, `010`, and `100`, with zero invalid probability.
- Every tested one-hot basis state remained in the one-hot subspace across four nontrivial mixer angles.
- No invalid sample appeared in 49,152 mixer-validation shots.
- The full unoptimized D=4 ansatz had invalid statevector probability `4.92e-33` and produced 0 invalid samples in 4,096 shots.
- The D=4 initial distribution was statistically consistent with uniform sampling across all 81 valid routes: chi-square p-value `0.98095`, total variation distance `0.02210`, and 0 invalid samples in 16,384 shots.
- All 81 valid assignments had the same Hamiltonian ordering as the frozen objective. There were zero pairwise ordering mismatches; maximum Qmod cost error was `1.91e-17`.
- Bit ordering and decoding were verified for every valid assignment.

This establishes that the mixer solves the routing-subspace access problem. The resulting one-hot probability of 1.0 is a construction invariant, not evidence of optimization quality.

### Optimization result against the correct control

Three independent optimizer seeds were run at D=4 with fixed uniform scenario weights, p=1, 512 optimizer shots per evaluation, 10 optimizer iterations, and 4,096 final shots. Each seed was compared with 1,000 uniform-random-valid batches of the same 4,096-sample size.

| Seed | One-hot | Jointly feasible | Near/exact optimum | Mean objective | Matched-control p-value for lower mean |
|---:|---:|---:|---:|---:|---:|
| 6601 | 1.000 | 0.3989 | 0.01025 | 0.35149 | 0.000999 |
| 6602 | 1.000 | 0.2861 | 0.00854 | 0.35747 | 0.8452 |
| 6603 | 1.000 | 0.4226 | 0.01001 | 0.35105 | 0.000999 |
| Uniform-valid population | 1.000 | 0.4815 | 0.01235 | 0.35615 | — |

Two seeds shifted mean cost downward, but the effect did not reproduce in seed 6602. Across seeds, the mean objective was `0.35334 ± 0.00358`, only a `0.79%` improvement over the uniform-valid population mean. A descriptive one-sided three-seed t-test gave p=`0.153`; with only three seeds this is not secure evidence.

More importantly, all three QAOA seeds placed less probability than uniform-valid sampling on jointly feasible, near-optimal, and exact-optimum routes. The matched-control p-values for near-optimal mass were `0.905`, `0.996`, and `0.917`. Best-sample metrics saturated because 4,096 valid samples cover a small 81-state search space, so distributional metrics are the meaningful comparison.

**Track A conclusion:** constrained QAOA is correct and eliminates invalid-subspace leakage, but p=1 does not demonstrate reproducible conditional optimization advantage over uniform-valid sampling.

### Resource cost and D=6 gate

For the same D=4 frozen uniform objective and p=1:

| Resource | X-mixer | Constrained mixer | Change |
|---|---:|---:|---:|
| Qubits | 12 | 12 | 0% |
| Synthesized depth | 65 | 101 | +55.4% (`1.55x`) |
| Total gates | 154 | 314 | +103.9% (`2.04x`) |
| Two-qubit gates | 84 | 164 | +95.2% (`1.95x`) |

The constrained circuit synthesized in `10.89 s`; the three optimizer runs took `12.16–13.43 s`. The resource comparison is hardware-agnostic and makes no backend-fidelity or monetary-cost claim.

The D=6 gate required every seed to beat at least 95% of matched uniform-valid batches on mean objective or near-optimal fraction. Seed 6602 failed the mean-objective criterion, and every seed was worse on near-optimal mass. The gate decision was `STOP_AT_D4`; no D=6 synthesis or execution was performed.

## Track B — evolution and generalization

### Reproduction and correctness

Before ablation, the original S=3, eta=1, T=3, rho=0 adaptive trajectory was reproduced to `1e-12`, including its route, weights, regret, and objective trajectory. The final weights were `(0.267068, 0.247085, 0.485847)`.

Every multiplicative update and diversity-mixing update was checked numerically for positivity, normalization, deterministic reproducibility, eta=0 behavior, monotonic pressure response, and contraction toward uniform under rho. All 192 configurations and every outer iteration were checked by exhaustive enumeration of all 81 routes, including exact tie retention.

The deterministic pools contained 12 nested training scenarios and 16 validation scenarios, with the existing 24 held-out scenarios kept as immutable final test data. IDs and parameter fingerprints were pairwise disjoint. Validation selected policies before final-test evaluation; no final-test result was used for tuning.

### What explains the original failure

The frozen original comparison was reproduced:

| Policy | Route | Final survival | Mean regret | Worst regret | Violations | Max overflow |
|---|---|---:|---:|---:|---:|---:|
| Static uniform, S=3 | `[1,0,2,2]` | 1.0000 | 0.07545 | 0.31631 | 0 | 0.0 |
| Adaptive, S=3, eta=1, T=3 | `[0,1,1,2]` | 0.9167 | 0.14699 | 0.47833 | 2 | 0.4 |

The ablation isolates four interacting causes:

1. **Training diversity S is the strongest stabilizer.** In the focused rho=0 grid, S=3 averaged survival `0.96875` and worst regret `0.37707`. S=5, 8, and 12 all averaged survival `1.0` and worst regret `0.31631`, converging to one robust route.
2. **High selection strength eta is harmful in the fragile small-S regime.** Eta 0 and 0.25 averaged survival `1.0` and worst regret `0.31631`; eta 0.5 degraded these to `0.98958` and `0.33656`; eta 1 degraded them to `0.97917` and `0.35682`. The harm was localized primarily to S=3.
3. **More iterations T amplify exposure rather than guaranteeing improvement.** T=3 averaged survival `0.99479` and worst regret `0.32644`; T=5 averaged `0.98958` and `0.33656`. Repeated exact best responses can cross route boundaries or cycle.
4. **Diversity mixing rho is an effective safeguard.** In 72 matched comparisons, rho changed the selected route in 7 cases; all 7 improved and none worsened. At affected settings, survival increased by `0.08333` and worst regret fell by `0.16202`. Aggregate rho=0.5 recovered survival `1.0` and worst regret `0.31631`.

### Weight collapse interpretation

The original adaptive run ended with `N_eff=2.854` out of 3, an effective fraction of `0.951`, and maximum weight `0.486`. This is meaningful concentration but not severe collapse.

Across eta>0, T>1 runs, concentration `1-N_eff/S` correlated with worse final worst regret (Pearson `0.402`, Spearman `0.443`). Within fixed S, Pearson correlations ranged from `0.517` to `0.884`. The data therefore support weight concentration as a risk indicator, but the mechanism is not simply catastrophic collapse: a modest shift in weights can cross a discontinuous exact-best-response boundary and select a route that is poorly matched to unseen capacity patterns.

The mismatch is reinforced by the training objective: the exact training domain has zero overflow, so multiplicative updates react to training regret without directly observing the held-out capacity failure mode.

### Does moderated adaptation beat static uniform weighting?

No. The validation-selected static policy and the validation-selected genuinely adaptive policy both chose route `[0,2,1,2]` and tied exactly on validation and final test:

| Policy | Parameters | Validation survival / worst regret | Final survival / worst regret |
|---|---|---:|---:|
| Static uniform | S=8, eta=0, T=1, rho=0 | 1.0 / 0.15882 | 1.0 / 0.31631 |
| Genuine adaptive | S=8, eta=0.1, T=2, rho=0 | 1.0 / 0.15882 | 1.0 / 0.31631 |

The original predeclared selector admitted eta>0, T=1, even though T=1 performs no update. That edge case was retained transparently. A validation-only eligibility supplement requiring eta>0 and T>1 selected the genuine adaptive policy above; it still only tied static uniform weighting.

**Track B conclusion:** S, eta, T, and rho explain when adaptation becomes harmful and how to control it. More diverse training and conservative/mixed updates prevent over-specialization, but the tested adaptive policies provide no positive generalization advantage over static uniform multi-scenario training.

## Independent lessons

### Quantum lesson

The Post-6A diagnosis was correct: the generic X-mixer wastes probability outside the routing subspace. A constraint-preserving mixer removes that bottleneck completely. Once conditioned on valid routes, however, this p=1 ansatz/optimizer does not concentrate probability on better routes reliably enough to outperform the correct uniform-valid baseline. Feasibility access and optimization advantage are separate claims.

### Evolution lesson

The biological pressure metaphor is not sufficient by itself. Multiplicative selection over a small or unrepresentative environment set can magnify a pressure that has no reliable relationship to unseen failure modes. Environmental diversity and a diversity floor make adaptation safer, but the current fixed-route objective still gives static uniform multi-scenario training at least equal generalization.

## Combined decision

The proposed combined algorithm would join:

- a constrained quantum component that is correct but more expensive and not conditionally superior at D=4; and
- an evolutionary component whose moderated forms recover, but do not exceed, the static uniform benchmark.

There is no evidence that their combination would create a benefit absent from both components, while the circuit overhead and additional outer-loop variance would make attribution harder. The Stage 6B D=6 gate also explicitly failed. The responsible next action is to keep the two results as valuable independent findings and not implement the combined algorithm under the current design.

COMBINED ADAPTIVE-CONSTRAINED QAOA: NO-GO
