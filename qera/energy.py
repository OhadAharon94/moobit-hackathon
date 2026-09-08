"""Immutable base/aligned energy specification and affine phase scaling."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Sequence

from qera.config import ENERGY_TOLERANCE
from qera.evaluate import Evaluator, all_assignments
from qera.instance import EDGE_ORDER, PATH_EDGES, SCENARIOS, capacity_for
from qera.qubo import (
    all_bitstates,
    assignment_from_bits,
    bits_from_assignment,
    build_qubo,
    evaluate_qubo,
)
from qera.types import BitState, QuboModel


def capacity_violation(bits: Sequence[int]) -> bool:
    """Return whether selected bits overflow any link in any training scenario."""

    if len(bits) != len(PATH_EDGES) * len(PATH_EDGES[0]):
        raise ValueError("bit vector has the wrong width")
    for scenario in SCENARIOS:
        loads = {edge: 0.0 for edge in EDGE_ORDER}
        for demand_index, demand_paths in enumerate(PATH_EDGES):
            for path_index, edges in enumerate(demand_paths):
                bit = int(bits[3 * demand_index + path_index])
                if bit not in (0, 1):
                    raise ValueError("capacity predicate expects binary values")
                if bit:
                    for edge in edges:
                        loads[edge] += scenario.volumes[demand_index]
        if any(
            loads[edge] > capacity_for(edge, scenario) + ENERGY_TOLERANCE
            for edge in EDGE_ORDER
        ):
            return True
    return False


@dataclass(frozen=True)
class EnergySpec:
    qubo: QuboModel
    energy_mode: str
    capacity_penalty: float | None
    phase_offset: float
    phase_scale: float
    verification_summary: MappingProxyType

    def unscaled_energy(self, bits: Sequence[int]) -> float:
        energy = evaluate_qubo(self.qubo, bits)
        if self.capacity_penalty is not None and capacity_violation(bits):
            energy += self.capacity_penalty
        return energy

    def transformed_energy(self, bits: Sequence[int]) -> float:
        return (self.unscaled_energy(bits) - self.phase_offset) / self.phase_scale


def _ground_states(spec: EnergySpec) -> tuple[float, tuple[BitState, ...]]:
    scored = tuple((tuple(bits), spec.unscaled_energy(bits)) for bits in all_bitstates())
    minimum = min(value for _, value in scored)
    states = tuple(
        bits for bits, value in scored if abs(value - minimum) <= ENERGY_TOLERANCE
    )
    return minimum, states


def build_energy_spec(
    evaluator: Evaluator,
    weights: Sequence[float],
    objective_mode: str,
    energy_mode: str = "base",
    capacity_penalty: float | None = None,
) -> EnergySpec:
    """Build a calibrated energy and validate all of its ground states."""

    qubo = build_qubo(evaluator, weights, objective_mode)
    if energy_mode not in {"base", "aligned"}:
        raise ValueError(f"unsupported energy mode: {energy_mode}")

    selected_penalty: float | None = None
    capacity_gap: float | None = None
    if energy_mode == "aligned":
        feasible = evaluator.joint_feasible_assignments()
        infeasible = tuple(
            assignment
            for assignment in all_assignments()
            if not evaluator.is_joint_feasible(assignment)
        )
        best_feasible = min(
            evaluate_qubo(qubo, bits_from_assignment(assignment)) for assignment in feasible
        )
        selected_penalty = 1.0 if capacity_penalty is None else float(capacity_penalty)
        while True:
            best_infeasible = min(
                evaluate_qubo(qubo, bits_from_assignment(assignment)) + selected_penalty
                for assignment in infeasible
            )
            capacity_gap = best_infeasible - best_feasible
            if capacity_gap > ENERGY_TOLERANCE:
                break
            if capacity_penalty is not None:
                raise ValueError(
                    f"capacity penalty {selected_penalty} does not align the ground state"
                )
            selected_penalty *= 2.0
            if selected_penalty > 1e9:
                raise RuntimeError("capacity penalty calibration failed")

    unscaled_values = []
    for bits in all_bitstates():
        value = evaluate_qubo(qubo, bits)
        if selected_penalty is not None and capacity_violation(bits):
            value += selected_penalty
        unscaled_values.append(value)
    phase_offset = min(unscaled_values)
    phase_scale = max(unscaled_values) - phase_offset
    if phase_scale <= ENERGY_TOLERANCE:
        phase_scale = 1.0

    provisional = EnergySpec(
        qubo=qubo,
        energy_mode=energy_mode,
        capacity_penalty=selected_penalty,
        phase_offset=phase_offset,
        phase_scale=phase_scale,
        verification_summary=MappingProxyType({}),
    )
    ground_energy, ground_states = _ground_states(provisional)
    ground_assignments = tuple(assignment_from_bits(bits) for bits in ground_states)
    if energy_mode == "aligned" and any(
        assignment is None or not evaluator.is_joint_feasible(assignment)
        for assignment in ground_assignments
    ):
        raise ValueError("aligned energy has an invalid or capacity-infeasible ground state")

    return EnergySpec(
        qubo=qubo,
        energy_mode=energy_mode,
        capacity_penalty=selected_penalty,
        phase_offset=phase_offset,
        phase_scale=phase_scale,
        verification_summary=MappingProxyType(
            {
                "capacity_gap": capacity_gap,
                "ground_energy": ground_energy,
                "ground_state_count": len(ground_states),
                "ground_assignments": ground_assignments,
                "all_ground_states_joint_feasible": all(
                    assignment is not None and evaluator.is_joint_feasible(assignment)
                    for assignment in ground_assignments
                ),
            }
        ),
    )
