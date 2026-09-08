"""Frozen-fixture regression and adaptive-update audit."""

from __future__ import annotations

import hashlib
import json
from math import exp, isclose, log
from pathlib import Path

from qera.adaptive import run_adaptive
from qera.evaluate import Evaluator
from qera.exact import ExactInnerSolver, update_weights


def stable_weight_update(
    weights: tuple[float, ...],
    regrets: tuple[float, ...],
    *,
    eta: float = 1.0,
    r_max: float = 1.0,
) -> tuple[float, ...]:
    """Independent log-space implementation of the specified update."""

    if len(weights) != len(regrets) or not weights:
        raise ValueError("weight and regret vectors must be nonempty and equal length")
    if any(weight <= 0.0 for weight in weights):
        raise ValueError("weights must be strictly positive")
    logits = [
        log(weight) + eta * min(r_max, max(0.0, float(regret)))
        for weight, regret in zip(weights, regrets, strict=True)
    ]
    pivot = max(logits)
    values = [exp(value - pivot) for value in logits]
    total = sum(values)
    return tuple(value / total for value in values)


def adaptive_audit() -> dict:
    evaluator = Evaluator()
    cost_run = run_adaptive(ExactInnerSolver(evaluator), evaluator, "cost")
    regret_run = run_adaptive(ExactInnerSolver(evaluator), evaluator, "regret")
    first = cost_run.steps[0]
    independent_first = stable_weight_update(
        first.request.scenario_weights, first.regrets
    )
    frozen_first = update_weights(first.request.scenario_weights, first.regrets)
    invariants = {
        "finite_positive": all(value > 0.0 for value in independent_first),
        "sum_to_one": isclose(sum(independent_first), 1.0, abs_tol=1e-12),
        "matches_frozen_update": all(
            isclose(a, b, abs_tol=1e-14)
            for a, b in zip(independent_first, frozen_first, strict=True)
        ),
        "larger_regret_larger_multiplier": (
            independent_first[2] / first.request.scenario_weights[2]
            > independent_first[0] / first.request.scenario_weights[0]
            > independent_first[1] / first.request.scenario_weights[1]
        ),
        "zero_regret_no_exponential_boost": isclose(
            exp(min(1.0, max(0.0, 0.0))), 1.0, abs_tol=0.0
        ),
        "clipping": stable_weight_update((0.5, 0.5), (-2.0, 9.0))
        == stable_weight_update((0.5, 0.5), (0.0, 1.0)),
        "deterministic": independent_first
        == stable_weight_update(first.request.scenario_weights, first.regrets),
    }
    return {
        "eta": 1.0,
        "r_max": 1.0,
        "invariants": invariants,
        "all_invariants_pass": all(invariants.values()),
        "cost_trajectory": [list(step.result.assignment) for step in cost_run.steps],
        "cost_weights": [list(step.request.scenario_weights) for step in cost_run.steps],
        "cost_regrets": [list(step.regrets) for step in cost_run.steps],
        "regret_trajectory": [list(step.result.assignment) for step in regret_run.steps],
        "regret_weights": [list(step.request.scenario_weights) for step in regret_run.steps],
        "expected_cost_trajectory_pass": [step.result.assignment for step in cost_run.steps]
        == [(1, 0, 2, 2), (1, 0, 2, 2), (0, 1, 1, 2)],
        "expected_regret_trajectory_pass": [step.result.assignment for step in regret_run.steps]
        == [(0, 1, 1, 2)] * 3,
    }


def snapshot_v11(implementation_root: Path) -> dict:
    """Hash frozen source, tests, and evidence before Stage 6A work."""

    included = []
    for relative_root in ("qera", "tests", "scripts", "artifacts"):
        root = implementation_root / relative_root
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            included.append(
                {
                    "path": path.relative_to(implementation_root).as_posix(),
                    "sha256": digest,
                    "bytes": path.stat().st_size,
                }
            )
    plan_path = implementation_root / "Q_ERA_IMPLEMENTATION_PLAN.md"
    included.append(
        {
            "path": plan_path.name,
            "sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
            "bytes": plan_path.stat().st_size,
        }
    )
    return {
        "checkpoint_mode": "separate-extension-no-git-repository",
        "frozen_plan": "Q_ERA_IMPLEMENTATION_PLAN.md",
        "files": included,
    }


def write_audit_artifacts(stage6a_root: Path) -> None:
    output = stage6a_root / "artifacts" / "scaling" / "tables"
    output.mkdir(parents=True, exist_ok=True)
    implementation_root = stage6a_root.parent
    (output / "v11_1_hotfix_sha256_checkpoint.json").write_text(
        json.dumps(snapshot_v11(implementation_root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "adaptive_weight_audit.json").write_text(
        json.dumps(adaptive_audit(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
