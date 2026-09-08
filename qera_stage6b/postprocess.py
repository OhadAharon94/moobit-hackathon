"""Saved-result processing and matched valid-route controls for Stage 6B."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import math
import random
from typing import Any

import pandas as pd

from qera.config import ENERGY_TOLERANCE
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.postprocess import process_sample_frame
from qera_scaling.qubo import ScalingEnergySpec


WEIGHTS = (1.0 / 3.0,) * 3
NEAR_OPTIMAL_GAP = 0.01
MATCHED_BATCHES = 1000


def every_seed_passes_quality_gate(
    mean_objective_pvalues: Sequence[float],
    near_optimal_pvalues: Sequence[float],
    *,
    alpha: float = 0.05,
) -> bool:
    """Return whether every seed passes at least one predeclared quality test."""

    if len(mean_objective_pvalues) != len(near_optimal_pvalues):
        raise ValueError("quality-gate p-value collections must have equal length")
    if not mean_objective_pvalues:
        return False
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between zero and one")
    pairs = zip(mean_objective_pvalues, near_optimal_pvalues, strict=True)
    return all(float(mean_p) <= alpha or float(near_p) <= alpha for mean_p, near_p in pairs)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0 or successes < 0 or successes > total:
        raise ValueError("invalid binomial count")
    probability = successes / total
    denominator = 1.0 + z * z / total
    center = (probability + z * z / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(
            probability * (1.0 - probability) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return center - half_width, center + half_width


def weighted_quantile(values: Sequence[float], counts: Sequence[int], q: float) -> float:
    if len(values) != len(counts) or not values:
        raise ValueError("values and counts must be nonempty and have equal length")
    if not 0.0 <= q <= 1.0:
        raise ValueError("quantile must be in [0,1]")
    pairs = sorted(zip(values, counts, strict=True))
    total = sum(count for _, count in pairs)
    if total <= 0:
        raise ValueError("counts must sum to a positive value")
    target = q * (total - 1)
    cumulative = 0
    for value, count in pairs:
        if cumulative + count > target:
            return float(value)
        cumulative += count
    return float(pairs[-1][0])


def distribution_metrics(processed: pd.DataFrame, summary: dict[str, Any]) -> dict[str, Any]:
    shots = int(summary["total_shots"])
    one_hot = processed[processed["one_hot"]].copy()
    if one_hot.empty:
        raise ValueError("constrained QAOA produced no one-hot samples")
    one_hot_count = int(one_hot["counts"].sum())
    feasible_count = int(one_hot.loc[one_hot["joint_feasible"], "counts"].sum())
    near = one_hot["joint_feasible"] & (
        one_hot["weighted_cost"]
        <= float(summary["exact_joint_objective"]) + NEAR_OPTIMAL_GAP
    )
    near_count = int(one_hot.loc[near, "counts"].sum())
    exact = one_hot["joint_feasible"] & (
        (one_hot["weighted_cost"] - float(summary["exact_joint_objective"])).abs()
        <= ENERGY_TOLERANCE
    )
    exact_count = int(one_hot.loc[exact, "counts"].sum())
    objective_values = [float(value) for value in one_hot["weighted_cost"]]
    counts = [int(value) for value in one_hot["counts"]]
    mean_objective = sum(
        value * count for value, count in zip(objective_values, counts, strict=True)
    ) / one_hot_count
    feasible = one_hot[one_hot["joint_feasible"]]
    best_regret = (
        float(feasible["worst_case_regret"].min()) if not feasible.empty else None
    )
    feasible_low, feasible_high = wilson_interval(feasible_count, one_hot_count)
    near_low, near_high = wilson_interval(near_count, one_hot_count)
    exact_low, exact_high = wilson_interval(exact_count, one_hot_count)
    return {
        "total_shots": shots,
        "one_hot_count": one_hot_count,
        "one_hot_probability": one_hot_count / shots,
        "joint_feasible_count": feasible_count,
        "joint_feasible_probability": feasible_count / shots,
        "feasible_fraction_valid": feasible_count / one_hot_count,
        "feasible_fraction_valid_wilson_low": feasible_low,
        "feasible_fraction_valid_wilson_high": feasible_high,
        "near_optimal_count": near_count,
        "near_optimal_probability": near_count / shots,
        "near_optimal_fraction_valid": near_count / one_hot_count,
        "near_optimal_fraction_valid_wilson_low": near_low,
        "near_optimal_fraction_valid_wilson_high": near_high,
        "exact_optimum_count": exact_count,
        "exact_optimum_probability": exact_count / shots,
        "exact_optimum_fraction_valid": exact_count / one_hot_count,
        "exact_optimum_fraction_valid_wilson_low": exact_low,
        "exact_optimum_fraction_valid_wilson_high": exact_high,
        "mean_valid_objective": mean_objective,
        "q25_valid_objective": weighted_quantile(objective_values, counts, 0.25),
        "median_valid_objective": weighted_quantile(objective_values, counts, 0.5),
        "q75_valid_objective": weighted_quantile(objective_values, counts, 0.75),
        "best_feasible_objective_gap": summary["selected_exact_gap"],
        "best_feasible_relative_gap": summary["selected_relative_gap"],
        "best_feasible_worst_case_regret": best_regret,
        "best_feasible_regret_gap": summary["best_sampled_regret_gap"],
        "near_optimal_absolute_gap_threshold": NEAR_OPTIMAL_GAP,
    }


def exact_uniform_valid_metrics(evaluator: ScalingEvaluator) -> dict[str, Any]:
    exact_cost, exact_routes, _ = evaluator.exact_optima(
        WEIGHTS,
        "cost",
        joint_feasible=True,
    )
    routes = tuple(evaluator.all_assignments())
    records = []
    for route in routes:
        objective = evaluator.weighted_objective(route, WEIGHTS, "cost")
        feasible = evaluator.is_joint_feasible(route)
        regret = max(
            evaluator.regret(route, scenario)
            for scenario in evaluator.instance.scenarios
        )
        records.append((objective, feasible, regret))
    objectives = sorted(item[0] for item in records)
    feasible_records = [item for item in records if item[1]]
    near_count = sum(
        item[1] and item[0] <= exact_cost + NEAR_OPTIMAL_GAP for item in records
    )
    return {
        "valid_state_count": len(routes),
        "joint_feasible_count": len(feasible_records),
        "feasible_fraction_valid": len(feasible_records) / len(routes),
        "near_optimal_count": near_count,
        "near_optimal_fraction_valid": near_count / len(routes),
        "exact_optimum_count": len(exact_routes),
        "exact_optimum_fraction_valid": len(exact_routes) / len(routes),
        "mean_valid_objective": sum(objectives) / len(objectives),
        "q25_valid_objective": weighted_quantile(objectives, [1] * len(objectives), 0.25),
        "median_valid_objective": weighted_quantile(objectives, [1] * len(objectives), 0.5),
        "q75_valid_objective": weighted_quantile(objectives, [1] * len(objectives), 0.75),
        "best_feasible_objective_gap": 0.0,
        "best_feasible_worst_case_regret": min(item[2] for item in feasible_records),
        "exact_joint_objective": exact_cost,
    }


def route_cache(evaluator: ScalingEvaluator) -> tuple[tuple, dict]:
    exact_cost, exact_routes, _ = evaluator.exact_optima(
        WEIGHTS,
        "cost",
        joint_feasible=True,
    )
    exact_set = set(exact_routes)
    domain = tuple(evaluator.all_assignments())
    cache = {}
    for route in domain:
        objective = evaluator.weighted_objective(route, WEIGHTS, "cost")
        feasible = evaluator.is_joint_feasible(route)
        cache[route] = {
            "objective": objective,
            "objective_gap": objective - exact_cost,
            "feasible": feasible,
            "near_optimal": feasible and objective <= exact_cost + NEAR_OPTIMAL_GAP,
            "exact_optimum": route in exact_set,
            "worst_case_regret": max(
                evaluator.regret(route, scenario)
                for scenario in evaluator.instance.scenarios
            ),
        }
    return domain, cache


def matched_uniform_valid_batches(
    evaluator: ScalingEvaluator,
    sample_count: int,
    *,
    seed: int,
    batches: int = MATCHED_BATCHES,
) -> list[dict[str, Any]]:
    if sample_count <= 0 or batches <= 0:
        raise ValueError("sample count and batch count must be positive")
    domain, cache = route_cache(evaluator)
    rng = random.Random(seed)
    rows = []
    for batch_index in range(batches):
        sampled = [cache[rng.choice(domain)] for _ in range(sample_count)]
        feasible = [item for item in sampled if item["feasible"]]
        objectives = [float(item["objective"]) for item in sampled]
        rows.append(
            {
                "batch_index": batch_index,
                "batch_seed": seed,
                "batch_size": sample_count,
                "joint_feasible_count": len(feasible),
                "feasible_fraction_valid": len(feasible) / sample_count,
                "near_optimal_count": sum(item["near_optimal"] for item in sampled),
                "near_optimal_fraction_valid": sum(
                    item["near_optimal"] for item in sampled
                )
                / sample_count,
                "exact_optimum_count": sum(item["exact_optimum"] for item in sampled),
                "exact_optimum_fraction_valid": sum(
                    item["exact_optimum"] for item in sampled
                )
                / sample_count,
                "mean_valid_objective": sum(objectives) / sample_count,
                "q25_valid_objective": weighted_quantile(
                    objectives, [1] * sample_count, 0.25
                ),
                "median_valid_objective": weighted_quantile(
                    objectives, [1] * sample_count, 0.5
                ),
                "q75_valid_objective": weighted_quantile(
                    objectives, [1] * sample_count, 0.75
                ),
                "best_feasible_objective_gap": (
                    min(item["objective_gap"] for item in feasible)
                    if feasible
                    else None
                ),
                "best_feasible_worst_case_regret": (
                    min(item["worst_case_regret"] for item in feasible)
                    if feasible
                    else None
                ),
            }
        )
    return rows


def empirical_pvalue(
    values: Iterable[float],
    observed: float,
    *,
    lower_is_better: bool,
) -> float:
    clean = [float(value) for value in values if pd.notna(value)]
    comparisons = (
        sum(value <= observed for value in clean)
        if lower_is_better
        else sum(value >= observed for value in clean)
    )
    return (comparisons + 1) / (len(clean) + 1)


def matched_control_summary(
    observed: dict[str, Any],
    batches: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    frame = pd.DataFrame(batches)
    metrics = {
        "feasible_fraction_valid": False,
        "near_optimal_fraction_valid": False,
        "exact_optimum_fraction_valid": False,
        "mean_valid_objective": True,
        "median_valid_objective": True,
        "best_feasible_objective_gap": True,
        "best_feasible_worst_case_regret": True,
    }
    summary: dict[str, Any] = {
        "matched_batch_count": len(frame),
        "matched_batch_size": int(frame["batch_size"].iloc[0]),
    }
    for metric, lower_is_better in metrics.items():
        values = frame[metric].dropna()
        observed_value = float(observed[metric])
        summary[f"qaoa_{metric}"] = observed_value
        summary[f"random_{metric}_mean"] = float(values.mean())
        summary[f"random_{metric}_median"] = float(values.median())
        summary[f"random_{metric}_q25"] = float(values.quantile(0.25))
        summary[f"random_{metric}_q75"] = float(values.quantile(0.75))
        summary[f"random_{metric}_min"] = float(values.min())
        summary[f"random_{metric}_max"] = float(values.max())
        summary[f"empirical_p_random_at_least_as_good_{metric}"] = empirical_pvalue(
            values,
            observed_value,
            lower_is_better=lower_is_better,
        )
    return summary


def process_saved_frame(
    frame: pd.DataFrame,
    evaluator: ScalingEvaluator,
    spec: ScalingEnergySpec,
    declared_shots: int,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    processed, summary = process_sample_frame(
        frame,
        evaluator,
        spec,
        WEIGHTS,
        declared_shots=declared_shots,
        approximation_threshold=NEAR_OPTIMAL_GAP,
    )
    return processed, summary, distribution_metrics(processed, summary)
