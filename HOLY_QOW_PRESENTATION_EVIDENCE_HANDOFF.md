# Holy QOW — Presentation Evidence Pack Handoff

**Purpose:** turn frozen evidence into presentation-ready plots, tables, demo assets, and judge Q&A.  
**Do not run new Classiq jobs. Do not redesign the algorithm.**

## 1. Final scientific story to preserve

### Robust-routing result
On the 24 frozen held-out stress scenarios:
- Nominal representative: **20/24 survival = 83.3%**, 4 violations.
- Static uniform multi-scenario route: **24/24 = 100%**, 0 violations.
- Original adaptive route: **22/24 = 91.7%**, 2 violations.

Correct claim: **training across diverse network conditions produced the only tested route that survived all 24 held-out stresses.**

Do not claim that adaptive/evolutionary reweighting improved generalization.

### Evolution result
The ablation showed:
- low training-environment diversity plus stronger selection pressure can cause a harmful discrete route switch;
- increasing training diversity to at least S=5 or mixing weights back toward uniform prevents the harmful switch;
- moderated adaptation did not beat static uniform weighting on final held-out performance.

Correct claim: **environmental diversity mattered more than stronger selection pressure.**

### Quantum result
At D=6 across five independent optimizer seeds:
- QAOA found a better best-feasible objective and best-feasible worst regret than paired uninformed random-bit sampling in **5/5 runs**;
- one-hot/feasible mass was highly seed-dependent;
- QAOA did **not** establish superiority over matched uniform-valid route sampling.

Correct claim: **QAOA learned enough structure to beat unstructured binary search, but not a baseline already restricted to the valid routing space.**

### Constraint-preserving mixer result
At D=4:
- the Dicke/W + XY-style mixer preserved one-hot structure exactly;
- one-hot probability rose from the frozen X-mixer's **5.225%** to **100%** by construction;
- depth: **65 -> 101**;
- total gates: **154 -> 314**;
- 2Q gates: **84 -> 164**;
- no reproducible p=1 route-quality advantage over uniform-valid sampling was established.

Correct claim: **the constrained mixer fixed the structural subspace problem, but p=1 optimization quality remained the next bottleneck.**

### Scalability result
Use:

| D | Qubits | Depth | 2Q gates |
|---:|---:|---:|---:|
| 4 | 12 | 65 | 84 |
| 5 | 15 | 79 | 136 |
| 6 | 18 | 138 | 160 |
| 8 | 24 | 246 | 280 |

D=8 is **synthesis-only**.

Correct claim: **for fixed K=3, route-register width grows linearly as 3D; depth and entangling-gate cost grow faster.**

No quantum-advantage claim.

---

## 2. Generate these MAIN presentation figures

All figures should be presentation-ready for a 16:9 slide: large labels, minimal text, white or transparent background, no tiny legends.

### MAIN-1 — Held-out robustness
Output:
`presentation_assets/01_heldout_survival.png`

Three bars:
- Nominal: 83.3%
- Static multi-environment: 100%
- Adaptive reweighting: 91.7%

Annotate violations: 4 / 0 / 2.

Optional small annotation: worst regret 0.235 / 0.316 / 0.478.

Headline/caption:
> **Static multi-environment routing survived all 24 unseen stress scenarios.**

Add a small note that the nominal route is one representative of a tied nominal optimum.

### MAIN-2 — Quantum resource scaling
Output:
`presentation_assets/02_quantum_scaling.png`

Use D=4,5,6,8.

Prefer two compact panels:
1. logical/synthesized qubits vs D;
2. depth and 2Q gates vs D.

Label D=8 as `synthesis only`.

Caption:
> **Logical width grows linearly; circuit depth and entangling cost grow faster.**

### MAIN-3 — D=6 repeated quantum evidence
Output:
`presentation_assets/03_d6_qaoa_vs_random_bits.png`

Read exact paired per-seed values from saved Post-6A artifacts.

Plot all five seeds comparing:
- QAOA best feasible objective gap;
- paired random-bit best feasible objective gap.

If clean, add a second panel for best feasible worst-case regret.

The visual should make the 5/5 direction obvious.

Caption:
> **QAOA found a better best-feasible route than uninformed random-bit sampling in all 5 D=6 runs.**

Directly below:
> **It did not outperform fair sampling restricted to valid routes.**

---

## 3. Generate these BACKUP figures

### BACKUP-1 — Evolution ablation
Output:
`presentation_assets/backup_01_evolution_ablation.png`

Show clearly:
- original static S=3: 100% final survival;
- original adaptive S=3, eta=1: 91.7%;
- S>=5 adaptive/focused settings: harmful switch disappears / 100% average survival;
- rho=0.5 aggregate: 100% survival.

Headline:
> **Too much selection pressure on too few environments caused over-specialization.**

Secondary line:
> More environment diversity or a diversity floor prevented the harmful switch.

Do not imply adaptation beats static.

### BACKUP-2 — Constraint-preserving mixer tradeoff
Output:
`presentation_assets/backup_02_constraint_mixer.png`

Show:
- X mixer one-hot: 5.225%
- constrained mixer one-hot: 100%
- depth: 65 vs 101
- 2Q gates: 84 vs 164

Text:
> **Structural problem solved; no reproducible route-quality advantage at p=1.**

### BACKUP-3 — Verification / auditability
Output:
`presentation_assets/backup_03_verification.png`

Concise proof card:
- 81 valid D=4 routes exhaustively evaluated;
- frozen QUBO/Ising check covers all 4096 bitstrings;
- integrated dual-track test suites: **132 passed, 0 failed**.

Caption:
> **Every small-instance quantum result was checked against exact classical ground truth.**

---

## 4. Create the presentation evidence table

Create:
`presentation_assets/PRESENTATION_NUMBERS.csv`

Columns:
`claim_id,slide,metric,value,unit,source_artifact,source_field_or_row,notes`

Every number intended for the presentation must point to a saved artifact.

Also create:
`presentation_assets/PRESENTATION_EVIDENCE_PACK.md`

For each candidate claim list:
- exact wording;
- supporting value(s);
- source artifact path;
- classification: MAIN / BACKUP / DO_NOT_USE.

---

## 5. Create a short embedded-demo asset

Target length: **20–35 seconds**.

Preferred output:
`presentation_assets/holy_qow_demo.mp4`

Use saved deterministic results only. Do not run anything live.

Suggested flow:
1. network + candidate routes;
2. nominal route;
3. apply an unseen capacity/demand stress;
4. highlight overload/failure of nominal route;
5. show static multi-environment route remaining feasible;
6. final card: `24/24 held-out scenarios survived` and `Classiq QAOA implemented for route selection`.

If video generation is unreliable, create numbered PNG storyboard frames plus `DEMO_STORYBOARD.md` with exact recording instructions.

Do not portray adaptive reweighting as the winning route.

---

## 6. Create a five-slide pitch script

Create:
`presentation_assets/PITCH_5MIN.md`

### Slide 1 — Problem (~45 s)
Core line:
> **The route that is optimal now may be fragile five minutes later.**

### Slide 2 — Holy QOW (~60 s)
Explain:
- classical K candidate paths per demand;
- multi-environment objective;
- Classiq QAOA selects globally coupled route combination;
- evaluate robustness across scenarios.

Biology line:
> We started from an evolutionary hypothesis: robust solutions should survive diverse environmental pressures.

Do not claim adaptive weighting was the winner.

### Slide 3 — Robustness result (~60 s)
Use MAIN-1.

Core line:
> **Static training across diverse environments was the only tested policy surviving all 24 held-out stress cases.**

One evolution insight:
> Aggressively overweighting the current weakest environment over-specialized on a small training set; diversity mattered more than stronger pressure.

### Slide 4 — Quantum implementation + scaling (~90 s)
Use MAIN-2 and/or MAIN-3.

Must say:
- Classiq QAOA implemented;
- synthesis scaled 12 -> 24 route qubits;
- D=6 repeated over five seeds;
- QAOA beat paired random-bit search 5/5;
- it did not beat sampling directly inside the valid route space.

### Slide 5 — What we learned (~45 s)
Three concise findings:
1. Robustness came from diverse network environments.
2. QAOA represents the coupled path-selection Hamiltonian and shows structure relative to random bits.
3. Constraint-preserving mixing fixes invalid-state waste, but p=1 optimization quality remains a limitation.

End:
> **From optimal today to resilient tomorrow.**

---

## 7. Create judge Q&A support

Create:
`presentation_assets/JUDGE_QA.md`

Give concise evidence-backed answers to:
1. Why quantum?
2. Did you demonstrate quantum advantage?
3. Why not Dijkstra?
4. Why not MILP/CP-SAT?
5. What is novel?
6. Does the evolutionary adaptation work?
7. Why did static weighting beat adaptive?
8. Is the approach scalable?
9. Why is D=8 synthesis-only?
10. Why implement a constrained mixer?
11. Why didn't the constrained mixer improve route quality?
12. What would you do next?
13. What is classical vs quantum in Holy QOW?

---

## 8. Claims to use / avoid

### USE if verified
- Candidate-path preprocessing isolates the globally coupled route-selection problem for QAOA.
- For fixed K, the route register grows as D*K.
- Static multi-environment routing survived all 24 frozen held-out stress scenarios.
- QAOA beat paired random-bit search on best feasible route quality in 5/5 D=6 seeds.
- QAOA did not demonstrate superiority over uniform sampling restricted to valid routes.
- The constrained mixer preserved one-hot routing exactly but roughly doubled gate cost and did not establish a reproducible p=1 quality gain.
- No quantum computational advantage is claimed.

### DO NOT USE
- Evolutionary adaptation improved generalization.
- Holy QOW beat classical optimization.
- QAOA beats random valid routing.
- Constraint-preserving QAOA solves scalability.
- D=8 QAOA was executed.
- We demonstrated quantum speedup/advantage.
- The adaptive route is the best robust route.
- Simulator runtime represents QPU runtime.
- Any invented AT&T financial savings.

---

## 9. Final fact-check

Create:
`presentation_assets/FINAL_FACT_CHECK.md`

PASS/FAIL all of these:
- every main-slide number traces to raw evidence;
- plots regenerate from saved CSV/JSON only;
- no plot mixes incomparable seeds/budgets;
- D=8 clearly says synthesis-only;
- adaptive and exact-minimax identical routes are not presented as independent confirmations;
- held-out scenarios are not described as training data;
- constrained-mixer D=6 is labeled NOT ATTEMPTED;
- no quantum-advantage language appears;
- demo contains no live dependency.

---

## 10. Final instruction

> **Do not perform new research and do not run new Classiq jobs. Turn the frozen evidence into a concise, traceable presentation pack. The final story is: diverse multi-environment routing improved held-out survival; aggressive evolutionary pressure over-specialized; Classiq QAOA was implemented and scaled in synthesis to 24 qubits; repeated D=6 QAOA beat uninformed random bits but not valid-route sampling; a constrained mixer fixed structural validity but not p=1 optimization quality. Preserve negative results honestly and make every claim traceable.**
