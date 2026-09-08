"""Decode saved Classiq samples through the shared evaluator."""

from __future__ import annotations

import ast
import json
from collections.abc import Sequence
from typing import Any

import pandas as pd

from qera.config import ENERGY_TOLERANCE
from qera.energy import EnergySpec
from qera.evaluate import Evaluator
from qera.exact import weighted_optima
from qera.instance import SCENARIOS
from qera.qubo import all_bitstates, assignment_from_bits, bits_from_assignment
from qera.types import Assignment, BitState


def parse_routes_cell(value: Any) -> BitState:
    """Parse Classiq's named QArray output without using bitstring conventions."""

    parsed = ast.literal_eval(value) if isinstance(value, str) else value
    if not isinstance(parsed, Sequence) or isinstance(parsed, (str, bytes)):
        raise ValueError(f"routes output is not a bit sequence: {value!r}")
    bits = tuple(int(bit) for bit in parsed)
    if len(bits) != 12 or any(bit not in (0, 1) for bit in bits):
        raise ValueError(f"routes output must contain 12 binary values: {value!r}")
    return bits


def _assignment_label(assignment: Assignment | None) -> str | None:
    return None if assignment is None else json.dumps(list(assignment))


def process_sample_frame(
    frame: pd.DataFrame,
    evaluator: Evaluator,
    spec: EnergySpec,
    weights: Sequence[float],
    objective_mode: str,
    *,
    declared_shots: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate, decode, evaluate, and summarize a raw Classiq sample frame."""

    required = {"routes", "counts"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"sample frame is missing columns: {sorted(missing)}")

    aggregated: dict[BitState, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        bits = parse_routes_cell(row["routes"])
        count = int(row["counts"])
        if count < 0:
            raise ValueError("sample counts cannot be negative")
        record = aggregated.setdefault(
            bits,
            {
                "bits": bits,
                "counts": 0,
                "provider_bitstrings": set(),
            },
        )
        record["counts"] += count
        if "bitstring" in row and pd.notna(row["bitstring"]):
            record["provider_bitstrings"].add(str(row["bitstring"]))

    total_shots = sum(record["counts"] for record in aggregated.values())
    if declared_shots is not None and total_shots != declared_shots:
        raise ValueError(
            f"decoded counts sum to {total_shots}, expected {declared_shots}"
        )

    rows: list[dict[str, Any]] = []
    for bits, record in aggregated.items():
        assignment = assignment_from_bits(bits)
        one_hot = assignment is not None
        joint_feasible = one_hot and evaluator.is_joint_feasible(assignment)
        scenario_costs = (
            {
                scenario.name: evaluator.evaluate(assignment, scenario).cost
                for scenario in SCENARIOS
            }
            if assignment is not None
            else {}
        )
        scenario_regrets = (
            {
                scenario.name: evaluator.regret(assignment, scenario)
                for scenario in SCENARIOS
            }
            if assignment is not None
            else {}
        )
        current_objective = (
            evaluator.weighted_objective(assignment, weights, objective_mode)
            if assignment is not None
            else None
        )
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
                "assignment": _assignment_label(assignment),
                "current_objective": current_objective,
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

    exact_joint_value, exact_joint_assignments = weighted_optima(
        evaluator, weights, objective_mode, joint_feasible=True
    )
    accepted = processed[processed["joint_feasible"]].copy()
    if accepted.empty:
        selected_assignment = None
        selected_objective = None
        exact_gap = None
        status = "NO_FEASIBLE_SAMPLE"
    else:
        accepted["assignment_tuple"] = accepted["assignment"].map(
            lambda value: tuple(json.loads(value))
        )
        selected_row = accepted.sort_values(
            ["current_objective", "assignment_tuple"], ascending=True
        ).iloc[0]
        selected_assignment = tuple(json.loads(selected_row["assignment"]))
        selected_objective = float(selected_row["current_objective"])
        exact_gap = selected_objective - exact_joint_value
        status = "SUCCESS"

    joint_optimum_bits = {
        bits_from_assignment(assignment) for assignment in exact_joint_assignments
    }
    joint_optimum_mass = sum(
        record["counts"] / total_shots
        for bits, record in aggregated.items()
        if bits in joint_optimum_bits
    )
    unrestricted_minimum = min(spec.unscaled_energy(bits) for bits in all_bitstates())
    unrestricted_ground_mass = sum(
        record["counts"] / total_shots
        for bits, record in aggregated.items()
        if abs(spec.unscaled_energy(bits) - unrestricted_minimum) <= ENERGY_TOLERANCE
    )
    near_optimal_mass = float(
        processed.loc[
            processed["joint_feasible"]
            & (processed["current_objective"] <= exact_joint_value + 0.01),
            "probability",
        ].sum()
    )

    summary = {
        "status": status,
        "total_shots": total_shots,
        "observed_state_count": len(processed),
        "one_hot_probability": one_hot_mass,
        "joint_feasible_probability": joint_mass,
        "unrestricted_ground_probability": unrestricted_ground_mass,
        "joint_optimum_probability": joint_optimum_mass,
        "near_optimal_joint_probability_gap_0_01": near_optimal_mass,
        "exact_joint_objective": exact_joint_value,
        "exact_joint_assignments": exact_joint_assignments,
        "selected_assignment": selected_assignment,
        "selected_objective": selected_objective,
        "selected_exact_gap": exact_gap,
    }
    return processed.drop(columns=[], errors="ignore"), summary
