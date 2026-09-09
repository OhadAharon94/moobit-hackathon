# Teammate branch review and integration assessment

**Review date:** 9 September 2026

**Reviewed branch:** `origin/fix/submission-portability`

**Reviewed commits:** `8feaef1`, `5b4ff50`
**Integration branch:** `dual-track-coordination`

## Outcome

The useful fixes were integrated. Two parts required correction before they were
safe and scientifically consistent with the current branch:

1. the proposed hybrid wrapper could replace a valid classical route with a
   failed, infeasible, or worse quantum result;
2. the global CSV line-ending rule broke the current Windows evidence hashes and
   did not make the complete Stage 6A evidence chain portable because the bound
   QPROG and synthesis JSON hashes remained line-ending dependent.

No saved quantum run, measured distribution, held-out result, Stage 6B result, or
evolution-ablation result was changed.

## Finding-by-finding decisions

### Accepted

- Future Stage 6A execution manifests record repository-relative QPROG and
  synthesis-manifest paths when possible.
- Legacy creator-machine absolute paths can relocate to the equivalent artifact
  in the active checkout. Existing SHA-256 and synthesis-spec validation still
  binds the relocated circuit to the requested instance and objective.
- Future CSV writers explicitly use LF line terminators.
- README installation commands now work from the repository root and include
  complete PowerShell and macOS/Linux setup instructions.
- Python/project branding and the human-readable adaptive trace were retained.
- Local review, Jupyter, and Matplotlib state directories are ignored.

### Revised

- `SelectiveHybridSolver` now treats quantum execution as a candidate-generation
  experiment, not an unconditional replacement. It returns a quantum route only
  when that route is successful, jointly feasible, and strictly better than the
  classical candidate by worst regret and then weighted objective. Quantum
  failure, infeasibility, regression, or an exact quality tie retains the valid
  classical result.
- Solver-owned `SolveResult` objects are no longer mutated while audit metadata
  is added.
- The operating-model document now labels regional decomposition and SDN
  integration as proposed, unimplemented architecture. It no longer says that
  difficult cases automatically combine QAOA with adaptive reweighting.
- The adaptive decision trace now labels its 63.6% reduction as an in-training
  result and explicitly states that adaptive routing did not beat static uniform
  multi-environment training on the frozen held-out set.

### Not accepted

- The global `*.csv text eol=lf` rule and its two rewritten raw-sample hashes were
  removed from the integration. On the current checkout, that rule immediately
  caused the D=6 processor to reject its frozen raw sample. It would also alter
  many later Post-6A, Stage 6B, evolution, and presentation CSV byte hashes.
- The rule was incomplete as a cross-platform solution: on the teammate commit,
  the Git-blob SHA-256 values for both D=5/D=6 QPROG files and both synthesis JSON
  files still differed from their recorded Windows hashes. A future hash-format
  migration must cover the entire provenance graph atomically; it should not be
  mixed into the submission branch immediately before presentation.

## Effect on the current branch

- **Behavioral safety improves:** a quantum escalation can no longer downgrade a
  usable classical answer.
- **Reproducibility improves for paths:** new manifests are checkout-relative and
  old absolute paths can be safely relocated through the existing hash guard.
- **Scientific claims stay unchanged:** static diverse multi-environment routing
  remains the held-out winner; adaptive reweighting may over-specialize; neither
  the X-mixer nor the constrained p=1 mixer establishes quantum advantage.
- **Frozen evidence remains intact:** the saved D=5/D=6 raw hashes match again,
  and the presentation audit reproduced all 172 checks and all six figures.
- **No runtime or numerical regression was observed:** 142 tests passed across
  the root, Stage 6A, Post-6A, Stage 6B, and evolution-ablation suites.

## Push recommendation

Push the reviewed integration branch, then merge it through a pull request rather
than pushing directly to `main`:

```powershell
git status --short --branch
git log --oneline --decorate -5
git push -u origin dual-track-coordination
```

The untracked `HOLY_QOW_PRESENTATION_EVIDENCE_HANDOFF.md` is intentionally not
part of the integration commit. Decide separately whether that authoritative
input document belongs in repository history. Do not force-push and do not
renormalize the evidence tree before the submission.
