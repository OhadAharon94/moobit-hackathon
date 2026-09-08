"""D=6 repeatability metrics with separate shot and optimizer-seed uncertainty."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable

import pandas as pd

from holy_qow_post6a.common import artifact_root, implementation_root

REPEAT_SEEDS = (6106, 6201, 6202, 6203, 6204)
CONTROL_OFFSETS = {
    "uniform_random_bitstrings": 100_000,
    "uniform_random_valid_routes": 200_000,
    "matched_random_valid_batches": 300_000,
}


def run_paths(seed: int) -> tuple[Path, Path, Path]:
    if seed == 6106:
        root = (
            implementation_root()
            / "stage6a"
            / "artifacts"
            / "scaling"
            / "qaoa"
            / "qera-d6-seed6106-p1-uniform-cost"
        )
    elif seed in REPEAT_SEEDS[1:]:
        root = artifact_root() / "repeatability" / "runs" / f"seed-{seed}"
    else:
        raise ValueError(f"unregistered Step 2 optimizer seed: {seed}")
    return root / "manifest.json", root / "samples_raw.csv", root / "optimizer.json"


def wilson_interval(
    successes: int, trials: int, confidence: float = 0.95
) -> tuple[float | None, float | None]:
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("invalid binomial counts")
    if trials == 0:
        return None, None
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between zero and one")
    z = NormalDist().inv_cdf(0.5 + confidence / 2.0)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denominator
    half_width = (
        z
        * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
        / denominator
    )
    return center - half_width, center + half_width


def probability_record(
    processed: pd.DataFrame,
    summary: dict[str, Any],
    *,
    optimizer_seed: int,
    method: str,
    random_seed: int | None,
) -> dict[str, Any]:
    shots = int(summary["total_shots"])
    onehot = int(processed.loc[processed["one_hot"], "counts"].sum())
    feasible = int(processed.loc[processed["joint_feasible"], "counts"].sum())
    near_mask = processed["joint_feasible"] & (
        processed["weighted_cost"]
        <= float(summary["exact_joint_objective"])
        + float(summary["approximation_threshold"])
    )
    near = int(processed.loc[near_mask, "counts"].sum())
    onehot_ci = wilson_interval(onehot, shots)
    feasible_ci = wilson_interval(feasible, shots)
    near_ci = wilson_interval(near, shots)
    conditional_feasible_ci = wilson_interval(feasible, onehot)
    conditional_near_ci = wilson_interval(near, onehot)
    accepted = processed[processed["joint_feasible"]]
    return {
        "D": 6,
        "optimizer_seed": optimizer_seed,
        "method": method,
        "control_random_seed": random_seed,
        "total_shots": shots,
        "one_hot_count": onehot,
        "joint_feasible_count": feasible,
        "near_optimal_count": near,
        "exact_joint_optimum_count": round(
            float(summary["exact_joint_optimum_probability"]) * shots
        ),
        "p_one_hot": onehot / shots,
        "p_one_hot_wilson95_low": onehot_ci[0],
        "p_one_hot_wilson95_high": onehot_ci[1],
        "p_joint_feasible": feasible / shots,
        "p_joint_feasible_wilson95_low": feasible_ci[0],
        "p_joint_feasible_wilson95_high": feasible_ci[1],
        "p_near_optimal": near / shots,
        "p_near_optimal_wilson95_low": near_ci[0],
        "p_near_optimal_wilson95_high": near_ci[1],
        "p_exact_joint_optimum": summary["exact_joint_optimum_probability"],
        "p_feasible_given_onehot": feasible / onehot if onehot else None,
        "p_feasible_given_onehot_wilson95_low": conditional_feasible_ci[0],
        "p_feasible_given_onehot_wilson95_high": conditional_feasible_ci[1],
        "p_near_optimal_given_onehot": near / onehot if onehot else None,
        "p_near_optimal_given_onehot_wilson95_low": conditional_near_ci[0],
        "p_near_optimal_given_onehot_wilson95_high": conditional_near_ci[1],
        "best_feasible_objective_gap": summary["selected_exact_gap"],
        "best_feasible_relative_gap": summary["selected_relative_gap"],
        "best_feasible_worst_case_regret": (
            float(accepted["worst_case_regret"].min())
            if not accepted.empty
            else None
        ),
        "best_feasible_regret_gap": summary["best_sampled_regret_gap"],
        "near_optimal_absolute_gap_threshold": summary[
            "approximation_threshold"
        ],
        "finite_shot_interval_method": "Wilson score, 95%",
    }


def optimizer_trace_rows(seed: int, trace: list[dict[str, Any]]) -> list[dict]:
    rows = []
    for item in trace:
        params = item["parameters"]["params"]
        rows.append(
            {
                "optimizer_seed": seed,
                "iteration": int(item["iteration"]),
                "reported_cost": float(item["cost"]),
                "gamma": float(params[0]),
                "beta": float(params[1]),
            }
        )
    return rows


def aggregate_optimizer_seed_variability(
    records: Iterable[dict[str, Any]], metrics: Iterable[str]
) -> list[dict[str, Any]]:
    frame = pd.DataFrame(records)
    frame = frame[frame["method"] == "qaoa"]
    rows = []
    for metric in metrics:
        values = pd.to_numeric(frame[metric], errors="coerce").dropna()
        rows.append(
            {
                "variability_source": "optimizer_seed",
                "metric": metric,
                "seed_count": int(len(values)),
                "mean": float(values.mean()),
                "sample_std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                "median": float(values.median()),
                "q25": float(values.quantile(0.25)),
                "q75": float(values.quantile(0.75)),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
            }
        )
    return rows


def load_manifest(seed: int) -> dict[str, Any]:
    manifest_path, _, _ = run_paths(seed)
    return json.loads(manifest_path.read_text(encoding="utf-8"))
