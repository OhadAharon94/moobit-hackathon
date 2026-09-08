"""Decode and compare Stage 6A sample distributions through the shared evaluator."""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Sequence
import json
import random
from typing import Any

import pandas as pd

from qera.config import ENERGY_TOLERANCE
from qera.validation import validated_integer
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.model import Assignment, BitState
from qera_scaling.qubo import (
    ScalingEnergySpec,
    assignment_from_bits,
    bits_from_assignment,
)


def parse_routes_cell(value: Any, variable_count: int) -> BitState:
    """Parse Classiq's named QArray output without relying on bitstring ordering."""

    parsed = ast.literal_eval(value) if isinstance(value, str) else value
    if not isinstance(parsed, Sequence) or isinstance(parsed, (str, bytes)):
        raise ValueError(f"routes output is not a bit sequence: {value!r}")
    if len(parsed) != variable_count:
        raise ValueError(
            f"routes output must contain {variable_count} binary values: {value!r}"
        )
    bits = tuple(
        validated_integer(bit, f"route bit {index}")
        for index, bit in enumerate(parsed)
    )
    if any(bit not in (0, 1) for bit in bits):
        raise ValueError(f"routes output must contain only binary values: {value!r}")
    return bits


def random_bitstring_frame(variable_count: int, shots: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    counts = Counter(
        tuple(rng.getrandbits(1) for _ in range(variable_count)) for _ in range(shots)
    )
    return pd.DataFrame(
        {
            "routes": [list(bits) for bits in counts],
            "counts": list(counts.values()),
            "bitstring": ["".join(str(bit) for bit in bits) for bits in counts],
        }
    )


def random_valid_route_frame(
    evaluator: ScalingEvaluator, shots: int, seed: int
) -> pd.DataFrame:
    rng = random.Random(seed)
    domain = tuple(evaluator.all_assignments())
    counts = Counter(rng.choice(domain) for _ in range(shots))
    bitstates = [bits_from_assignment(evaluator, route) for route in counts]
    return pd.DataFrame(
        {
            "routes": [list(bits) for bits in bitstates],
            "counts": list(counts.values()),
            "bitstring": ["".join(str(bit) for bit in bits) for bits in bitstates],
        }
    )


def _label(assignment: Assignment | None) -> str | None:
    return None if assignment is None else json.dumps(list(assignment))


def process_sample_frame(
    frame: pd.DataFrame,
    evaluator: ScalingEvaluator,
    spec: ScalingEnergySpec,
    weights: Sequence[float],
    *,
    declared_shots: int | None = None,
    approximation_threshold: float = 0.01,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate, strictly decode, filter, and score one saved sample frame."""

    missing = {"routes", "counts"}.difference(frame.columns)
    if missing:
        raise ValueError(f"sample frame is missing columns: {sorted(missing)}")
    if approximation_threshold < 0:
        raise ValueError("approximation threshold cannot be negative")

    variable_count = evaluator.instance.variable_count
    aggregated: dict[BitState, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        bits = parse_routes_cell(row["routes"], variable_count)
        count = validated_integer(row["counts"], "sample count")
        if count < 0:
            raise ValueError("sample counts cannot be negative")
        record = aggregated.setdefault(
            bits, {"counts": 0, "provider_bitstrings": set()}
        )
        record["counts"] += count
        if "bitstring" in row and pd.notna(row["bitstring"]):
            record["provider_bitstrings"].add(str(row["bitstring"]))

    total_shots = sum(record["counts"] for record in aggregated.values())
    if total_shots <= 0:
        raise ValueError("sample counts must sum to a positive number")
    if declared_shots is not None and total_shots != declared_shots:
        raise ValueError(f"decoded counts sum to {total_shots}, expected {declared_shots}")

    rows: list[dict[str, Any]] = []
    for bits, record in aggregated.items():
        assignment = assignment_from_bits(evaluator, bits)
        one_hot = assignment is not None
        joint_feasible = bool(one_hot and evaluator.is_joint_feasible(assignment))
        if assignment is None:
            scenario_costs: dict[str, float] = {}
            scenario_regrets: dict[str, float] = {}
            weighted_cost = None
            worst_case_regret = None
        else:
            scenario_costs = {
                scenario.name: evaluator.evaluate(assignment, scenario).cost
                for scenario in evaluator.instance.scenarios
            }
            scenario_regrets = {
                scenario.name: evaluator.regret(assignment, scenario)
                for scenario in evaluator.instance.scenarios
            }
            weighted_cost = evaluator.weighted_objective(assignment, weights, "cost")
            worst_case_regret = max(scenario_regrets.values())
        rows.append(
            {
                "routes": json.dumps(list(bits)),
                "canonical_bitstring": "".join(str(bit) for bit in bits),
                "provider_bitstrings": json.dumps(
                    sorted(record["provider_bitstrings"])
                ),
                "counts": record["counts"],
                "probability": record["counts"] / total_shots,
                "one_hot": one_hot,
                "joint_feasible": joint_feasible,
                "assignment": _label(assignment),
                "weighted_cost": weighted_cost,
                "worst_case_regret": worst_case_regret,
                "base_energy": spec.unscaled_energy(bits),
                "transformed_energy": spec.transformed_energy(bits),
                "scenario_costs": json.dumps(scenario_costs, sort_keys=True),
                "scenario_regrets": json.dumps(scenario_regrets, sort_keys=True),
            }
        )
    processed = pd.DataFrame(rows).sort_values(
        ["counts", "canonical_bitstring"], ascending=[False, True]
    )
    one_hot_mass = float(processed.loc[processed["one_hot"], "probability"].sum())
    joint_mass = float(
        processed.loc[processed["joint_feasible"], "probability"].sum()
    )

    exact_cost, exact_routes, _ = evaluator.exact_optima(
        weights, "cost", joint_feasible=True
    )
    feasible_routes = evaluator.joint_feasible_assignments()
    exact_minimax = min(
        max(evaluator.regret(route, scenario) for scenario in evaluator.instance.scenarios)
        for route in feasible_routes
    )
    exact_minimax_routes = tuple(
        route
        for route in feasible_routes
        if abs(
            max(
                evaluator.regret(route, scenario)
                for scenario in evaluator.instance.scenarios
            )
            - exact_minimax
        )
        <= ENERGY_TOLERANCE
    )

    accepted = processed[processed["joint_feasible"]].copy()
    if accepted.empty:
        status = "NO_FEASIBLE_SAMPLE"
        selected_assignment = None
        selected_objective = None
        selected_exact_gap = None
        selected_relative_gap = None
        best_regret_assignment = None
        best_sampled_regret = None
        best_regret_gap = None
    else:
        selected = accepted.sort_values(
            ["weighted_cost", "assignment"], ascending=True
        ).iloc[0]
        selected_assignment = tuple(json.loads(selected["assignment"]))
        selected_objective = float(selected["weighted_cost"])
        selected_exact_gap = selected_objective - exact_cost
        selected_relative_gap = (
            selected_exact_gap / abs(exact_cost)
            if abs(exact_cost) > ENERGY_TOLERANCE
            else selected_exact_gap
        )
        best_regret = accepted.sort_values(
            ["worst_case_regret", "assignment"], ascending=True
        ).iloc[0]
        best_regret_assignment = tuple(json.loads(best_regret["assignment"]))
        best_sampled_regret = float(best_regret["worst_case_regret"])
        best_regret_gap = best_sampled_regret - exact_minimax
        status = "SUCCESS"

    exact_bits = {bits_from_assignment(evaluator, route) for route in exact_routes}
    exact_mass = sum(
        record["counts"] / total_shots
        for bits, record in aggregated.items()
        if bits in exact_bits
    )
    minimax_bits = {
        bits_from_assignment(evaluator, route) for route in exact_minimax_routes
    }
    minimax_mass = sum(
        record["counts"] / total_shots
        for bits, record in aggregated.items()
        if bits in minimax_bits
    )
    unrestricted_ground_mass = sum(
        record["counts"] / total_shots
        for bits, record in aggregated.items()
        if abs(spec.unscaled_energy(bits) - spec.phase_offset) <= ENERGY_TOLERANCE
    )
    near_optimal_mass = float(
        processed.loc[
            processed["joint_feasible"]
            & (processed["weighted_cost"] <= exact_cost + approximation_threshold),
            "probability",
        ].sum()
    )
    summary = {
        "status": status,
        "total_shots": total_shots,
        "observed_state_count": len(processed),
        "one_hot_probability": one_hot_mass,
        "theoretical_uniform_one_hot_probability": (3.0 / 8.0)
        ** evaluator.instance.demand_count,
        "joint_feasible_probability": joint_mass,
        "unrestricted_ground_probability": unrestricted_ground_mass,
        "exact_joint_optimum_probability": exact_mass,
        "exact_minimax_probability": minimax_mass,
        "near_optimal_joint_probability_gap_0_01": near_optimal_mass,
        "exact_joint_objective": exact_cost,
        "exact_joint_assignments": exact_routes,
        "exact_minimax_regret": exact_minimax,
        "exact_minimax_assignments": exact_minimax_routes,
        "selected_assignment": selected_assignment,
        "selected_objective": selected_objective,
        "selected_exact_gap": selected_exact_gap,
        "selected_relative_gap": selected_relative_gap,
        "best_sampled_regret_assignment": best_regret_assignment,
        "best_sampled_worst_case_regret": best_sampled_regret,
        "best_sampled_regret_gap": best_regret_gap,
        "approximation_threshold": approximation_threshold,
    }
    return processed, summary
