"""Explicit QUBO construction, one-hot calibration, and Ising conversion."""

from __future__ import annotations

from itertools import product
from math import isclose
from types import MappingProxyType
from typing import Iterable, Sequence

from qera.config import (
    CONGESTION_WEIGHT,
    DEMAND_COUNT,
    ENERGY_TOLERANCE,
    LATENCY_WEIGHT,
    PATHS_PER_DEMAND,
    VARIABLE_COUNT,
    variable_index,
)
from qera.evaluate import Evaluator, all_assignments
from qera.instance import DEMANDS, EDGE_ORDER, LINK_BY_EDGE, PATH_EDGES, SCENARIOS, capacity_for
from qera.types import Assignment, BitState, IsingModel, QuboModel


def all_bitstates() -> Iterable[BitState]:
    """Iterate over all 2^12 binary states in canonical variable order."""

    return product((0, 1), repeat=VARIABLE_COUNT)


def bits_from_assignment(assignment: Sequence[int]) -> BitState:
    if len(assignment) != DEMAND_COUNT:
        raise ValueError("assignment must contain one choice per demand")
    bits = [0] * VARIABLE_COUNT
    for demand_index, path_index in enumerate(assignment):
        bits[variable_index(demand_index, int(path_index))] = 1
    return tuple(bits)


def assignment_from_bits(bits: Sequence[int]) -> Assignment | None:
    if len(bits) != VARIABLE_COUNT or any(int(value) not in (0, 1) for value in bits):
        raise ValueError(f"expected {VARIABLE_COUNT} binary values")
    choices: list[int] = []
    for demand_index in range(DEMAND_COUNT):
        active = [
            path_index
            for path_index in range(PATHS_PER_DEMAND)
            if bits[variable_index(demand_index, path_index)] == 1
        ]
        if len(active) != 1:
            return None
        choices.append(active[0])
    return tuple(choices)  # type: ignore[return-value]


def is_one_hot(bits: Sequence[int]) -> bool:
    return assignment_from_bits(bits) is not None


def evaluate_qubo(model: QuboModel, bits: Sequence[int]) -> float:
    if len(bits) != len(model.linear):
        raise ValueError("bit vector length does not match QUBO")
    return (
        model.offset
        + sum(coefficient * int(bits[index]) for index, coefficient in enumerate(model.linear))
        + sum(
            coefficient * int(bits[left]) * int(bits[right])
            for (left, right), coefficient in model.quadratic.items()
        )
    )


def evaluate_ising(model: IsingModel, bits: Sequence[int]) -> float:
    if len(bits) != len(model.linear):
        raise ValueError("bit vector length does not match Ising model")
    spins = tuple(1 - 2 * int(bit) for bit in bits)
    return (
        model.offset
        + sum(coefficient * spins[index] for index, coefficient in enumerate(model.linear))
        + sum(
            coefficient * spins[left] * spins[right]
            for (left, right), coefficient in model.quadratic.items()
        )
    )


def _add_quadratic(
    quadratic: dict[tuple[int, int], float], left: int, right: int, value: float
) -> None:
    if left == right:
        raise ValueError("diagonal QUBO terms belong in the linear vector")
    key = (left, right) if left < right else (right, left)
    quadratic[key] = quadratic.get(key, 0.0) + value


def _scenario_cost_polynomial(
    evaluator: Evaluator, scenario_index: int
) -> tuple[float, list[float], dict[tuple[int, int], float]]:
    scenario = SCENARIOS[scenario_index]
    normalizer = evaluator.normalizations[scenario.name]
    offset = 0.0
    linear = [0.0] * VARIABLE_COUNT
    quadratic: dict[tuple[int, int], float] = {}

    if normalizer.latency.span > ENERGY_TOLERANCE:
        offset -= LATENCY_WEIGHT * normalizer.latency.minimum / normalizer.latency.span
        for demand_index, demand in enumerate(DEMANDS):
            volume = scenario.volumes[demand_index]
            for path_index, edges in enumerate(PATH_EDGES[demand_index]):
                path_latency = sum(LINK_BY_EDGE[edge].latency for edge in edges)
                index = variable_index(demand_index, path_index)
                linear[index] += (
                    LATENCY_WEIGHT
                    * volume
                    * demand.priority
                    * path_latency
                    / normalizer.latency.span
                )

    if normalizer.congestion.span > ENERGY_TOLERANCE:
        offset -= (
            CONGESTION_WEIGHT
            * normalizer.congestion.minimum
            / normalizer.congestion.span
        )
        for edge in EDGE_ORDER:
            capacity = capacity_for(edge, scenario)
            terms: list[tuple[int, float]] = []
            for demand_index in range(DEMAND_COUNT):
                volume = scenario.volumes[demand_index]
                for path_index in range(PATHS_PER_DEMAND):
                    if edge in PATH_EDGES[demand_index][path_index]:
                        terms.append((variable_index(demand_index, path_index), volume))
            scale = CONGESTION_WEIGHT / (
                normalizer.congestion.span * capacity * capacity
            )
            for index, load in terms:
                linear[index] += scale * load * load
            for position, (left, left_load) in enumerate(terms):
                for right, right_load in terms[position + 1 :]:
                    _add_quadratic(
                        quadratic, left, right, 2.0 * scale * left_load * right_load
                    )

    return offset, linear, quadratic


def _objective_polynomial(
    evaluator: Evaluator, weights: Sequence[float], mode: str
) -> tuple[float, list[float], dict[tuple[int, int], float]]:
    if len(weights) != len(SCENARIOS):
        raise ValueError("one weight is required per scenario")
    offset = 0.0
    linear = [0.0] * VARIABLE_COUNT
    quadratic: dict[tuple[int, int], float] = {}
    for scenario_index, (scenario, weight) in enumerate(
        zip(SCENARIOS, weights, strict=True)
    ):
        scenario_offset, scenario_linear, scenario_quadratic = _scenario_cost_polynomial(
            evaluator, scenario_index
        )
        affine_scale = float(weight)
        affine_shift = 0.0
        if mode == "regret":
            reference = evaluator.regret_references[scenario.name]
            if reference.span <= ENERGY_TOLERANCE:
                continue
            affine_scale /= reference.span
            affine_shift = -float(weight) * reference.optimum / reference.span
        elif mode != "cost":
            raise ValueError(f"unsupported objective mode: {mode}")
        offset += affine_scale * scenario_offset + affine_shift
        for index, coefficient in enumerate(scenario_linear):
            linear[index] += affine_scale * coefficient
        for pair, coefficient in scenario_quadratic.items():
            _add_quadratic(quadratic, *pair, affine_scale * coefficient)
    return offset, linear, quadratic


def _with_one_hot_penalty(
    objective: tuple[float, list[float], dict[tuple[int, int], float]], penalty: float
) -> QuboModel:
    offset, source_linear, source_quadratic = objective
    linear = list(source_linear)
    quadratic = dict(source_quadratic)
    for demand_index in range(DEMAND_COUNT):
        offset += penalty
        indices = [
            variable_index(demand_index, path_index)
            for path_index in range(PATHS_PER_DEMAND)
        ]
        for index in indices:
            linear[index] -= penalty
        for position, left in enumerate(indices):
            for right in indices[position + 1 :]:
                _add_quadratic(quadratic, left, right, 2.0 * penalty)
    cleaned = {
        pair: value
        for pair, value in quadratic.items()
        if not isclose(value, 0.0, abs_tol=1e-15)
    }
    variable_map = {
        variable_index(demand_index, path_index): (demand_index, path_index)
        for demand_index in range(DEMAND_COUNT)
        for path_index in range(PATHS_PER_DEMAND)
    }
    return QuboModel(
        offset=offset,
        linear=tuple(linear),
        quadratic=MappingProxyType(cleaned),
        one_hot_penalty=penalty,
        variable_map=MappingProxyType(variable_map),
    )


def build_qubo(
    evaluator: Evaluator,
    weights: Sequence[float],
    objective_mode: str,
    one_hot_penalty: float | None = None,
) -> QuboModel:
    """Build and, by default, calibrate the explicit QUBO."""

    objective = _objective_polynomial(evaluator, weights, objective_mode)
    valid_states = tuple(bits_from_assignment(assignment) for assignment in all_assignments())
    valid_minimum = min(
        evaluate_qubo(_with_one_hot_penalty(objective, 0.0), bits)
        for bits in valid_states
    )
    penalty = 1.0 if one_hot_penalty is None else float(one_hot_penalty)
    while True:
        model = _with_one_hot_penalty(objective, penalty)
        invalid_minimum = min(
            evaluate_qubo(model, bits) for bits in all_bitstates() if not is_one_hot(bits)
        )
        gap = invalid_minimum - valid_minimum
        if gap > ENERGY_TOLERANCE:
            break
        if one_hot_penalty is not None:
            raise ValueError(
                f"one-hot penalty {penalty} does not separate invalid states (gap={gap})"
            )
        penalty *= 2.0
        if penalty > 1e9:
            raise RuntimeError("one-hot penalty calibration failed")
    return QuboModel(
        offset=model.offset,
        linear=model.linear,
        quadratic=model.quadratic,
        one_hot_penalty=model.one_hot_penalty,
        variable_map=model.variable_map,
        verification_summary=MappingProxyType(
            {
                "valid_minimum": valid_minimum,
                "invalid_minimum": invalid_minimum,
                "invalid_ground_gap": gap,
            }
        ),
    )


def qubo_to_ising(model: QuboModel) -> IsingModel:
    linear = [-coefficient / 2.0 for coefficient in model.linear]
    for (left, right), coefficient in model.quadratic.items():
        linear[left] -= coefficient / 4.0
        linear[right] -= coefficient / 4.0
    return IsingModel(
        offset=(
            model.offset
            + sum(model.linear) / 2.0
            + sum(model.quadratic.values()) / 4.0
        ),
        linear=tuple(linear),
        quadratic=MappingProxyType(
            {pair: coefficient / 4.0 for pair, coefficient in model.quadratic.items()}
        ),
    )
