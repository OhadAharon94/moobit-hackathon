"""Conditional-distribution and matched-valid analysis for saved QAOA shots."""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
from typing import Any

import pandas as pd

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.postprocess import process_sample_frame
from qera_scaling.qubo import build_energy_spec

from holy_qow_post6a.common import implementation_root

WEIGHTS = (1.0 / 3.0,) * 3
NEAR_OPTIMAL_GAP = 0.01
MATCHED_BATCHES = 1000


def qaoa_input_paths(D: int) -> tuple[Path, Path, Path]:
    root = implementation_root()
    if D == 4:
        run = root / "artifacts" / "runs" / "uniform_cost_p1_smoke"
    elif D in (5, 6):
        instance = generate_instance(D)
        run = (
            root
            / "stage6a"
            / "artifacts"
            / "scaling"
            / "qaoa"
            / f"{instance.instance_id}-p1-uniform-cost"
        )
    else:
        raise ValueError("Step 0 is restricted to existing D=4,5,6 QAOA runs")
    return run / "samples_raw.csv", run / "summary.json", run / "manifest.json"


def load_reprocessed_qaoa(D: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    instance = generate_instance(D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    raw_path, _, manifest_path = qaoa_input_paths(D)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shots = int(manifest["final_shots"])
    return process_sample_frame(
        pd.read_csv(raw_path),
        evaluator,
        spec,
        WEIGHTS,
        declared_shots=shots,
        approximation_threshold=NEAR_OPTIMAL_GAP,
    )


def conditional_record(D: int, processed: pd.DataFrame, summary: dict) -> dict:
    shots = int(summary["total_shots"])
    one_hot_count = int(processed.loc[processed["one_hot"], "counts"].sum())
    feasible_count = int(
        processed.loc[processed["joint_feasible"], "counts"].sum()
    )
    near_mask = processed["joint_feasible"] & (
        processed["weighted_cost"]
        <= float(summary["exact_joint_objective"]) + NEAR_OPTIMAL_GAP
    )
    near_count = int(processed.loc[near_mask, "counts"].sum())
    if one_hot_count <= 0:
        raise ValueError(f"D={D} has no one-hot samples; conditional metrics undefined")
    p_one_hot = one_hot_count / shots
    p_feasible = feasible_count / shots
    p_near = near_count / shots
    p_feasible_given_onehot = feasible_count / one_hot_count
    p_near_given_onehot = near_count / one_hot_count
    p_near_given_feasible = near_count / feasible_count if feasible_count else None
    factorized = p_one_hot * p_near_given_onehot
    onehot = processed[processed["one_hot"]]
    feasible = onehot[onehot["joint_feasible"]]
    return {
        "D": D,
        "total_shots": shots,
        "one_hot_count": one_hot_count,
        "joint_feasible_count": feasible_count,
        "near_optimal_count": near_count,
        "p_one_hot": p_one_hot,
        "p_joint_feasible": p_feasible,
        "p_near_optimal": p_near,
        "p_feasible_given_onehot": p_feasible_given_onehot,
        "p_near_optimal_given_onehot": p_near_given_onehot,
        "p_near_optimal_given_feasible": p_near_given_feasible,
        "factorized_near_optimal_probability": factorized,
        "factorization_residual": p_near - factorized,
        "best_feasible_objective_gap": summary["selected_exact_gap"],
        "best_feasible_relative_gap": summary["selected_relative_gap"],
        "best_feasible_worst_case_regret": (
            float(feasible["worst_case_regret"].min()) if not feasible.empty else None
        ),
        "near_optimal_absolute_gap_threshold": NEAR_OPTIMAL_GAP,
    }


def _route_cache(evaluator: ScalingEvaluator, exact_cost: float) -> dict:
    cache = {}
    for route in evaluator.all_assignments():
        feasible = evaluator.is_joint_feasible(route)
        objective = evaluator.weighted_objective(route, WEIGHTS, "cost")
        worst_regret = max(
            evaluator.regret(route, scenario)
            for scenario in evaluator.instance.scenarios
        )
        cache[route] = {
            "feasible": feasible,
            "objective_gap": objective - exact_cost,
            "near_optimal": feasible and objective <= exact_cost + NEAR_OPTIMAL_GAP,
            "worst_regret": worst_regret,
        }
    return cache


def matched_valid_batches(
    D: int,
    sample_count: int,
    *,
    batches: int = MATCHED_BATCHES,
    seed: int | None = None,
) -> list[dict]:
    if sample_count <= 0 or batches < 1:
        raise ValueError("matched batch size and batch count must be positive")
    evaluator = ScalingEvaluator(generate_instance(D))
    exact_cost, _, _ = evaluator.exact_optima(WEIGHTS, "cost", joint_feasible=True)
    cache = _route_cache(evaluator, exact_cost)
    domain = tuple(cache)
    selected_seed = 9000 + D if seed is None else int(seed)
    rng = random.Random(selected_seed)
    rows = []
    for batch_index in range(batches):
        sampled = [cache[rng.choice(domain)] for _ in range(sample_count)]
        feasible = [item for item in sampled if item["feasible"]]
        rows.append(
            {
                "D": D,
                "batch_index": batch_index,
                "batch_seed": selected_seed,
                "batch_size": sample_count,
                "joint_feasible_count": len(feasible),
                "joint_feasible_fraction": len(feasible) / sample_count,
                "near_optimal_count": sum(item["near_optimal"] for item in sampled),
                "near_optimal_fraction": sum(
                    item["near_optimal"] for item in sampled
                )
                / sample_count,
                "best_objective_gap": (
                    min(item["objective_gap"] for item in feasible)
                    if feasible
                    else None
                ),
                "best_worst_case_regret": (
                    min(item["worst_regret"] for item in feasible)
                    if feasible
                    else None
                ),
            }
        )
    return rows


def _empirical_pvalue(values: pd.Series, observed: float, *, lower_is_better: bool) -> float:
    valid = values.dropna()
    comparisons = valid <= observed if lower_is_better else valid >= observed
    return (int(comparisons.sum()) + 1) / (len(valid) + 1)


def matched_summary(
    conditional: dict, matched_rows: list[dict]
) -> dict[str, Any]:
    frame = pd.DataFrame(matched_rows)
    best_gap = float(conditional["best_feasible_objective_gap"])
    best_regret = float(conditional["best_feasible_worst_case_regret"])
    qaoa_near = float(conditional["p_near_optimal_given_onehot"])
    qaoa_feasible = float(conditional["p_feasible_given_onehot"])

    def distribution(prefix: str, column: str) -> dict:
        values = frame[column].dropna()
        return {
            f"random_{prefix}_mean": float(values.mean()),
            f"random_{prefix}_median": float(values.median()),
            f"random_{prefix}_q25": float(values.quantile(0.25)),
            f"random_{prefix}_q75": float(values.quantile(0.75)),
            f"random_{prefix}_min": float(values.min()),
            f"random_{prefix}_max": float(values.max()),
        }

    return {
        "D": conditional["D"],
        "matched_batch_count": len(frame),
        "matched_batch_size": conditional["one_hot_count"],
        "qaoa_best_objective_gap": best_gap,
        "qaoa_best_worst_case_regret": best_regret,
        "qaoa_feasible_fraction_given_onehot": qaoa_feasible,
        "qaoa_near_optimal_fraction_given_onehot": qaoa_near,
        **distribution("best_objective_gap", "best_objective_gap"),
        **distribution("best_worst_case_regret", "best_worst_case_regret"),
        **distribution("feasible_fraction", "joint_feasible_fraction"),
        **distribution("near_optimal_fraction", "near_optimal_fraction"),
        "empirical_p_random_best_gap_at_least_as_good": _empirical_pvalue(
            frame["best_objective_gap"], best_gap, lower_is_better=True
        ),
        "empirical_p_random_best_regret_at_least_as_good": _empirical_pvalue(
            frame["best_worst_case_regret"], best_regret, lower_is_better=True
        ),
        "empirical_p_random_feasible_fraction_at_least_as_high": _empirical_pvalue(
            frame["joint_feasible_fraction"], qaoa_feasible, lower_is_better=False
        ),
        "empirical_p_random_near_fraction_at_least_as_high": _empirical_pvalue(
            frame["near_optimal_fraction"], qaoa_near, lower_is_better=False
        ),
        "batches_without_feasible_route": int(
            frame["best_objective_gap"].isna().sum()
        ),
    }


def assert_finite_record(record: dict) -> None:
    for key, value in record.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"non-finite conditional metric {key}")
