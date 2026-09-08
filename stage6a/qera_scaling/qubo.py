"""Variable-width QUBO construction preserving the frozen coefficient convention."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import product
from math import isclose
from typing import Iterable, Mapping, Sequence

from qera.config import CONGESTION_WEIGHT, ENERGY_TOLERANCE, LATENCY_WEIGHT
from qera.validation import validated_integer

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.model import Assignment, BitState


@dataclass(frozen=True)
class ScalingQubo:
    offset: float
    linear: tuple[float, ...]
    quadratic: Mapping[tuple[int, int], float]
    one_hot_penalty: float
    verification_summary: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ScalingEnergySpec:
    qubo: ScalingQubo
    phase_offset: float
    phase_scale: float
    range_mode: str

    def unscaled_energy(self, bits: Sequence[int]) -> float:
        return evaluate_qubo(self.qubo, bits)

    def transformed_energy(self, bits: Sequence[int]) -> float:
        return (self.unscaled_energy(bits) - self.phase_offset) / self.phase_scale


def all_bitstates(variable_count: int) -> Iterable[BitState]:
    return product((0, 1), repeat=variable_count)


def bits_from_assignment(evaluator: ScalingEvaluator, assignment: Sequence[int]) -> BitState:
    route = evaluator.validate_assignment(assignment)
    bits = [0] * evaluator.instance.variable_count
    for demand_index, path_index in enumerate(route):
        bits[evaluator.instance.variable_index(demand_index, path_index)] = 1
    return tuple(bits)


def assignment_from_bits(
    evaluator: ScalingEvaluator, bits: Sequence[int]
) -> Assignment | None:
    instance = evaluator.instance
    if len(bits) != instance.variable_count:
        raise ValueError("bit vector has the wrong width")
    validated = tuple(
        validated_integer(value, f"route bit {index}")
        for index, value in enumerate(bits)
    )
    if any(value not in (0, 1) for value in validated):
        raise ValueError("bit vector has the wrong width or nonbinary values")
    choices = []
    for demand_index in range(instance.demand_count):
        active = [
            path_index
            for path_index in range(instance.paths_per_demand)
            if validated[instance.variable_index(demand_index, path_index)] == 1
        ]
        if len(active) != 1:
            return None
        choices.append(active[0])
    return tuple(choices)


def evaluate_qubo(model: ScalingQubo, bits: Sequence[int]) -> float:
    if len(bits) != len(model.linear):
        raise ValueError("bit vector length does not match QUBO")
    validated = tuple(
        validated_integer(value, f"route bit {index}")
        for index, value in enumerate(bits)
    )
    if any(value not in (0, 1) for value in validated):
        raise ValueError("QUBO inputs must be binary")
    return (
        model.offset
        + sum(value * validated[index] for index, value in enumerate(model.linear))
        + sum(
            value * validated[left] * validated[right]
            for (left, right), value in model.quadratic.items()
        )
    )


def _add_quadratic(
    coefficients: dict[tuple[int, int], float], left: int, right: int, value: float
) -> None:
    if left == right:
        raise ValueError("diagonal terms belong in the linear vector")
    pair = (left, right) if left < right else (right, left)
    coefficients[pair] = coefficients.get(pair, 0.0) + value


def _scenario_polynomial(
    evaluator: ScalingEvaluator, scenario_index: int
) -> tuple[float, list[float], dict[tuple[int, int], float]]:
    instance = evaluator.instance
    scenario = instance.scenarios[scenario_index]
    normalizer = evaluator.normalizations[scenario.name]
    offset = 0.0
    linear = [0.0] * instance.variable_count
    quadratic: dict[tuple[int, int], float] = {}
    if normalizer.latency.span > ENERGY_TOLERANCE:
        offset -= LATENCY_WEIGHT * normalizer.latency.minimum / normalizer.latency.span
        for demand_index, demand in enumerate(instance.demands):
            volume = scenario.volumes[demand_index]
            for path_index, edges in enumerate(instance.path_edges[demand_index]):
                path_latency = sum(instance.link_by_edge[edge].latency for edge in edges)
                index = instance.variable_index(demand_index, path_index)
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
        for edge in instance.edge_order:
            capacity = instance.capacity_for(edge, scenario)
            terms = []
            for demand_index in range(instance.demand_count):
                volume = scenario.volumes[demand_index]
                for path_index in range(instance.paths_per_demand):
                    if edge in instance.path_edges[demand_index][path_index]:
                        terms.append(
                            (instance.variable_index(demand_index, path_index), volume)
                        )
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
    evaluator: ScalingEvaluator, weights: Sequence[float], mode: str
) -> tuple[float, list[float], dict[tuple[int, int], float]]:
    instance = evaluator.instance
    if len(weights) != instance.scenario_count:
        raise ValueError("one weight is required per scenario")
    offset = 0.0
    linear = [0.0] * instance.variable_count
    quadratic: dict[tuple[int, int], float] = {}
    for index, (scenario, weight) in enumerate(
        zip(instance.scenarios, weights, strict=True)
    ):
        scenario_offset, scenario_linear, scenario_quadratic = _scenario_polynomial(
            evaluator, index
        )
        affine_scale = float(weight)
        affine_shift = 0.0
        if mode == "regret":
            reference = evaluator.regret_references[scenario.name]
            if reference.span <= ENERGY_TOLERANCE:
                continue
            affine_scale /= reference.span
            affine_shift = -float(weight) * reference.minimum / reference.span
        elif mode != "cost":
            raise ValueError(f"unsupported objective mode: {mode}")
        offset += affine_scale * scenario_offset + affine_shift
        for variable, value in enumerate(scenario_linear):
            linear[variable] += affine_scale * value
        for pair, value in scenario_quadratic.items():
            _add_quadratic(quadratic, *pair, affine_scale * value)
    return offset, linear, quadratic


def _with_one_hot_penalty(
    evaluator: ScalingEvaluator,
    objective: tuple[float, list[float], dict[tuple[int, int], float]],
    penalty: float,
) -> ScalingQubo:
    offset, source_linear, source_quadratic = objective
    linear = list(source_linear)
    quadratic = dict(source_quadratic)
    instance = evaluator.instance
    for demand_index in range(instance.demand_count):
        offset += penalty
        indices = [
            instance.variable_index(demand_index, path_index)
            for path_index in range(instance.paths_per_demand)
        ]
        for index in indices:
            linear[index] -= penalty
        for position, left in enumerate(indices):
            for right in indices[position + 1 :]:
                _add_quadratic(quadratic, left, right, 2.0 * penalty)
    return ScalingQubo(
        offset=offset,
        linear=tuple(linear),
        quadratic={
            pair: value
            for pair, value in quadratic.items()
            if not isclose(value, 0.0, abs_tol=1e-15)
        },
        one_hot_penalty=penalty,
    )


def _structured_invalid_states(
    evaluator: ScalingEvaluator, random_samples: int, seed: int
) -> Iterable[BitState]:
    instance = evaluator.instance
    seen: set[BitState] = set()
    anchors = [
        (0,) * instance.variable_count,
        (1,) * instance.variable_count,
    ]
    for bits in anchors:
        seen.add(bits)
        yield bits
    for assignment in evaluator.all_assignments():
        valid = list(bits_from_assignment(evaluator, assignment))
        for demand_index in range(instance.demand_count):
            selected = assignment[demand_index]
            removed = list(valid)
            removed[instance.variable_index(demand_index, selected)] = 0
            state = tuple(removed)
            if state not in seen:
                seen.add(state)
                yield state
            added = list(valid)
            added[
                instance.variable_index(
                    demand_index, (selected + 1) % instance.paths_per_demand
                )
            ] = 1
            state = tuple(added)
            if state not in seen:
                seen.add(state)
                yield state
    rng = random.Random(seed)
    for _ in range(random_samples):
        state = tuple(rng.getrandbits(1) for _ in range(instance.variable_count))
        if state not in seen and assignment_from_bits(evaluator, state) is None:
            seen.add(state)
            yield state


def build_qubo(
    evaluator: ScalingEvaluator,
    weights: Sequence[float],
    objective_mode: str,
    *,
    exhaustive_bit_limit: int = 18,
    invalid_sample_count: int = 100_000,
) -> ScalingQubo:
    objective = _objective_polynomial(evaluator, weights, objective_mode)
    objective_model = _with_one_hot_penalty(evaluator, objective, 0.0)
    valid_states = tuple(
        bits_from_assignment(evaluator, route) for route in evaluator.all_assignments()
    )
    direct_errors = [
        abs(
            evaluate_qubo(objective_model, bits)
            - evaluator.weighted_objective(route, weights, objective_mode)
        )
        for route, bits in zip(evaluator.all_assignments(), valid_states, strict=True)
    ]
    valid_minimum = min(evaluate_qubo(objective_model, bits) for bits in valid_states)
    exact = evaluator.instance.variable_count <= exhaustive_bit_limit
    if exact:
        invalid_states: Iterable[BitState] = tuple(
            bits
            for bits in all_bitstates(evaluator.instance.variable_count)
            if assignment_from_bits(evaluator, bits) is None
        )
        validation_mode = "exhaustive"
    else:
        invalid_states = tuple(
            _structured_invalid_states(
                evaluator, invalid_sample_count, evaluator.instance.seed + 97
            )
        )
        validation_mode = "structured-plus-seeded-sample"
    penalty = 1.0
    while True:
        model = _with_one_hot_penalty(evaluator, objective, penalty)
        invalid_minimum = min(evaluate_qubo(model, bits) for bits in invalid_states)
        gap = invalid_minimum - valid_minimum
        if gap > ENERGY_TOLERANCE:
            break
        penalty *= 2.0
        if penalty > 1e9:
            raise RuntimeError("one-hot penalty calibration failed")
    return ScalingQubo(
        offset=model.offset,
        linear=model.linear,
        quadratic=model.quadratic,
        one_hot_penalty=model.one_hot_penalty,
        verification_summary={
            "valid_minimum": valid_minimum,
            "invalid_minimum": invalid_minimum,
            "invalid_ground_gap": gap,
            "invalid_validation_mode": validation_mode,
            "invalid_states_checked": len(invalid_states),  # type: ignore[arg-type]
            "maximum_one_hot_objective_error": max(direct_errors, default=0.0),
        },
    )


def build_energy_spec(
    evaluator: ScalingEvaluator, weights: Sequence[float], objective_mode: str
) -> ScalingEnergySpec:
    qubo = build_qubo(evaluator, weights, objective_mode)
    variable_count = evaluator.instance.variable_count
    if variable_count <= 18:
        values = [evaluate_qubo(qubo, bits) for bits in all_bitstates(variable_count)]
        minimum, maximum = min(values), max(values)
        range_mode = "exhaustive"
    else:
        minimum = qubo.offset + sum(min(0.0, value) for value in qubo.linear)
        minimum += sum(min(0.0, value) for value in qubo.quadratic.values())
        maximum = qubo.offset + sum(max(0.0, value) for value in qubo.linear)
        maximum += sum(max(0.0, value) for value in qubo.quadratic.values())
        range_mode = "coefficient-bounds"
    scale = maximum - minimum
    if scale <= ENERGY_TOLERANCE:
        scale = 1.0
    return ScalingEnergySpec(qubo, minimum, scale, range_mode)


def qubo_metrics(spec: ScalingEnergySpec) -> dict:
    n = len(spec.qubo.linear)
    possible = n * (n - 1) // 2
    degrees = [0] * n
    for left, right in spec.qubo.quadratic:
        degrees[left] += 1
        degrees[right] += 1
    return {
        "logical_bits": n,
        "nonzero_linear": sum(not isclose(value, 0.0, abs_tol=1e-15) for value in spec.qubo.linear),
        "nonzero_quadratic": len(spec.qubo.quadratic),
        "possible_quadratic_pairs": possible,
        "quadratic_density": len(spec.qubo.quadratic) / possible if possible else 0.0,
        "mean_interaction_degree": sum(degrees) / n if n else 0.0,
        "max_interaction_degree": max(degrees, default=0),
        "one_hot_penalty_M": spec.qubo.one_hot_penalty,
        "qubo_energy_min_or_bound": spec.phase_offset,
        "qubo_energy_max_or_bound": spec.phase_offset + spec.phase_scale,
        "qubo_energy_range": spec.phase_scale,
        "energy_range_mode": spec.range_mode,
        **spec.qubo.verification_summary,
    }
