# Holy Qow adaptive decision trace

Every saved step is recoverable from inputs, scenario weights, quantum samples, feasibility checks, and deterministic tie-breaking.

| Step | Scenario weights (nominal / surge / degradation) | Selected route | Worst regret | Decision explanation |
|---:|---|---|---:|---|
| 1 | 0.333 / 0.333 / 0.333 | `[1, 0, 2, 2]` | 0.338 | Highest regret: degradation (0.338); next weight: degradation 0.333→0.407. |
| 2 | 0.302 / 0.291 / 0.407 | `[1, 0, 2, 2]` | 0.338 | Highest regret: degradation (0.338); next weight: degradation 0.407→0.486. |
| 3 | 0.267 / 0.247 / 0.486 | `[0, 1, 1, 2]` | 0.123 | Final solve; choose the lowest worst-regret route observed. |

Across the three frozen training scenarios, the best observed worst-case regret changed from **0.338** at the first step to **0.123** (63.6% lower).
This is an in-training trace, not a held-out robustness result; the adaptive route did not beat static uniform multi-environment training on the frozen 24-scenario held-out set.
