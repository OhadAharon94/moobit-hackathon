# Holy Qow adaptive decision trace

Every recommendation is recoverable from saved inputs, scenario weights, quantum samples, feasibility checks, and deterministic tie-breaking.

| Step | Scenario weights (nominal / surge / degradation) | Selected route | Worst regret | Decision explanation |
|---:|---|---|---:|---|
| 1 | 0.333 / 0.333 / 0.333 | `[1, 0, 2, 2]` | 0.338 | Highest regret: degradation (0.338); next weight: degradation 0.333→0.407. |
| 2 | 0.302 / 0.291 / 0.407 | `[1, 0, 2, 2]` | 0.338 | Highest regret: degradation (0.338); next weight: degradation 0.407→0.486. |
| 3 | 0.267 / 0.247 / 0.486 | `[0, 1, 1, 2]` | 0.123 | Final solve; choose the lowest worst-regret route observed. |

The best observed worst-case regret improved from **0.338** to **0.123** (63.6% reduction).
