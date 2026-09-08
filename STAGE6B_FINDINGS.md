# Holy QOW Stage 6B — Constraint-Preserving QAOA Findings

## Scope and decision

Track A tested a one-hot-preserving QAOA construction under the frozen D=4 instance and fixed uniform scenario weights only. It did not use adaptive scenario reweighting or any implementation produced by Track B.

The constraint-preserving construction is mathematically and empirically correct. It removes the X-mixer's dominant structural failure: every measured D=4 sample was a valid one-hot route assignment. However, the three-seed experiment did **not** establish a reproducible optimization advantage over uniform random valid routes. The predeclared D=6 quality gate therefore failed, and no D=6 circuit was synthesized or executed.

## Correctness gates

All mandatory D=4 correctness gates passed:

- The frozen v1.1, Stage 6A, and Post-6A test suites passed before implementation.
- A single three-qubit demand was initialized with the exact Dicke/W state, with probability `1/3` on each of `001`, `010`, and `100` and zero probability outside the one-excitation subspace.
- The pairwise mixer implements `exp[-i beta (XX + YY)]` using `RXX(2 beta)` followed by `RYY(2 beta)`. Exact statevector checks covered all three one-hot basis inputs at four nontrivial beta values. Invalid probability was at most numerical tolerance, and all 49,152 validation shots were one-hot.
- The full D=4 unoptimized ansatz remained one-hot: invalid statevector probability was `4.92e-33`, and all 4,096 sampled assignments were structurally valid.
- The initial D=4 state was uniform over all `3^4 = 81` valid routes. Its maximum statevector probability error from `1/81` was `2.31e-16`. A 16,384-shot check gave chi-square `56.014` on 80 degrees of freedom (`p = 0.98095`) and total-variation distance `0.02210`.
- Exhaustive evaluation of all 81 valid routes found zero cost-ordering mismatches against the frozen objective. The maximum Qmod cost reconstruction error was `1.91e-17`.
- The measured-bit decoding covered all 81 valid routes correctly, and every recorded sample count summed to its requested shot total.
- All three predeclared optimizer seeds completed, including the unfavorable seed; no poor run was discarded.

The implementation therefore answers the structural question positively: the one-hot state preparation and XY mixer preserve the intended feasible routing subspace exactly, up to floating-point tolerance in statevector output.

## D=4 optimization results

Each seed used the same synthesized p=1 circuit, initial parameters `[0.5, 0.5]`, ten optimizer iterations, 512 optimizer shots per objective evaluation, and 4,096 final shots. Each result was compared against 1,000 uniform-valid batches containing exactly 4,096 routes.

| Optimizer seed | One-hot | Joint feasible | Near-optimal / exact optimum | Mean objective | Matched-batch p, mean objective | Matched-batch p, near-optimal |
|---:|---:|---:|---:|---:|---:|---:|
| 6601 | 1.0000 | 0.3989 | 0.01025 | 0.35149 | 0.000999 | 0.9051 |
| 6602 | 1.0000 | 0.2861 | 0.00854 | 0.35747 | 0.8452 | 0.9960 |
| 6603 | 1.0000 | 0.4226 | 0.01001 | 0.35105 | 0.000999 | 0.9171 |
| Uniform-valid population | 1.0000 | 0.4815 | 0.01235 | 0.35615 | — | — |

Lower mean objective is better. The matched-batch p-value is the fraction of uniform-valid batches at least as good as the corresponding QAOA result, with the standard plus-one correction.

Two seeds improved the mean objective relative to every one of their 1,000 matched uniform-valid batches, but seed 6602 was worse than the uniform-valid population mean. Across seeds, the mean objective was `0.35334 +/- 0.00358`, an average improvement of only `0.00282` (`0.79%`) relative to the exact uniform-valid population mean. A descriptive one-sided t-test over only three seed means gave `p = 0.153`; it is not evidence of a seed-stable advantage.

More importantly, every seed placed **less** mass on jointly feasible routes and on the exact/near-optimal route than uniform-valid sampling. The average joint-feasible probability was `0.3692` versus `0.4815`, and the average near-optimal probability was `0.00960` versus `0.01235`. At 4,096 valid shots, both methods frequently observe the unique exact optimum, so the best-observed objective gap is zero for every seed and is not a discriminating success metric at this budget.

The result is therefore mixed but not ambiguous in its decision consequence: constrained QAOA slightly reshaped the bulk cost distribution for two seeds, while failing to improve the high-quality tail and failing to reproduce the mean-cost improvement across all seeds.

## Relation to the frozen X-mixer result

The frozen D=4 X-mixer run had one-hot probability `0.05225`; the constraint-preserving circuit raises this to `1.0` by construction. This is a structural improvement, not an optimization victory. Conditional on being one-hot, the earlier X-mixer run had jointly feasible probability `0.4486` and near-optimal probability `0.00935`. The constrained runs' high-quality mass remains comparable to or below uniform-valid sampling once the valid-space entry problem has been removed.

This isolates the bottleneck more precisely: the generic X-mixer wasted almost all shots outside the route subspace, but valid-subspace access was not the only limitation. With p=1 and the tested optimizer budget, the constrained cost landscape still did not concentrate probability reproducibly on the best valid routes.

## Circuit-resource tradeoff

Both circuits use 12 qubits. Relative to the frozen D=4 p=1 X-mixer circuit, the constraint-preserving circuit increased:

| Resource | X-mixer | Constraint-preserving | Change |
|---|---:|---:|---:|
| Synthesized depth | 65 | 101 | `+55.4%` (`1.55x`) |
| Total gates | 154 | 314 | `+103.9%` (`2.04x`) |
| Two-qubit gates | 84 | 164 | `+95.2%` (`1.95x`) |
| Width | 12 | 12 | unchanged |

The constraint-preserving synthesis took `10.89 s`, and the three hybrid optimizer runs took `12.16–13.43 s` each in the current simulator environment. The frozen X-mixer evidence did not record comparable synthesis or optimizer runtimes, so no runtime ratio is claimed. The resource comparison is hardware-agnostic; depth 101 and 164 two-qubit gates make this a marginal NISQ circuit, and no backend fidelity or execution-cost claim is made.

## D=6 gate decision

The predeclared gate required all three D=4 executions to succeed with one-hot samples **and** every seed to beat at least 95% of matched uniform-valid batches on mean objective or near-optimal probability.

The structural and execution conditions passed, but the quality condition failed: seed 6602 did not pass on mean objective, and no seed passed on near-optimal probability. D=6 is therefore **not justified by the frozen gate**. Its status is `NOT_ATTEMPTED`; no D=6 synthesis or quantum execution was performed.

## Evidence map

- `artifacts/stage6b/stage6b_stateprep_validation.json`
- `artifacts/stage6b/stage6b_mixer_preservation.json`
- `artifacts/stage6b/d4/d4_correctness_gates.json`
- `artifacts/stage6b/d4/aggregate_summary.json`
- `artifacts/stage6b/d4/statistical_summary.json`
- `artifacts/stage6b/d6/gate_decision.json`
- `artifacts/stage6b/tables/stage6b_d4_results.csv`
- `artifacts/stage6b/tables/stage6b_d4_seed_summary.csv`
- `artifacts/stage6b/tables/circuit_resource_comparison.csv`
- `artifacts/stage6b/figures/`

## Track A conclusion

1. **Did the mixer preserve one-hot structure exactly?** Yes, analytically and in all statevector and shot-based tests.
2. **What overhead did it introduce?** No extra qubits, but approximately `1.55x` depth, `2.04x` total gates, and `1.95x` two-qubit gates relative to the frozen p=1 X-mixer circuit.
3. **Did it beat uniform-valid sampling?** Not consistently. Two seeds improved mean cost, but none improved the near-optimal or feasible probability.
4. **Was any advantage reproducible?** No. The only favorable distributional signal was seed-dependent and not statistically secure across three seeds.
5. **Is D=6 justified/successful?** No. The predeclared D=4 gate failed, so D=6 was not attempted.

**TRACK A D=6 RECOMMENDATION: NO-GO**
