"""Single source of truth for Q-ERA route metrics and feasibility."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isclose
from types import MappingProxyType
from typing import Iterable, Sequence

from qera.config import (
    CAPACITY_TOLERANCE,
    CONGESTION_WEIGHT,
    DEMAND_COUNT,
    LATENCY_WEIGHT,
    PATHS_PER_DEMAND,
)
from qera.instance import (
    DEMANDS,
    EDGE_ORDER,
    LINK_BY_EDGE,
    PATH_EDGES,
    SCENARIO_BY_NAME,
    SCENARIOS,
    capacity_for,
)
from qera.types import (
    Assignment,
    ComponentRange,
    Edge,
    RegretReference,
    Scenario,
    ScenarioEvaluation,
    ScenarioNormalization,
)


def all_assignments() -> tuple[Assignment, ...]:
    """Enumerate the 3^4 structurally valid route assignments."""

    return tuple(product(range(PATHS_PER_DEMAND), repeat=DEMAND_COUNT))  # type: ignore[return-value]


def validate_assignment(assignment: Sequence[int]) -> Assignment:
    if len(assignment) != DEMAND_COUNT:
        raise ValueError(f"expected {DEMAND_COUNT} path choices, got {len(assignment)}")
    result = tuple(int(value) for value in assignment)
    if any(value < 0 or value >= PATHS_PER_DEMAND for value in result):
        raise ValueError(f"path choices must be in [0, {PATHS_PER_DEMAND - 1}]")
    return result  # type: ignore[return-value]


def _scenario(value: str | Scenario) -> Scenario:
    if isinstance(value, Scenario):
        return value
    try:
        return SCENARIO_BY_NAME[value]
    except KeyError as error:
        raise ValueError(f"unknown scenario: {value}") from error


@dataclass(frozen=True)
class RawEvaluation:
    latency: float
    congestion: float
    loads: MappingProxyType
    utilization: MappingProxyType
    maximum_utilization: float
    overflow: float
    feasible: bool


def raw_evaluate(
    assignment: Sequence[int], scenario: str | Scenario
) -> RawEvaluation:
    """Evaluate unnormalized latency, congestion, loads, and feasibility."""

    route = validate_assignment(assignment)
    active_scenario = _scenario(scenario)
    loads: dict[Edge, float] = {edge: 0.0 for edge in EDGE_ORDER}
    total_latency = 0.0

    for demand_index, path_index in enumerate(route):
        demand = DEMANDS[demand_index]
        volume = active_scenario.volumes[demand_index]
        edges = PATH_EDGES[demand_index][path_index]
        total_latency += volume * demand.priority * sum(
            LINK_BY_EDGE[edge].latency for edge in edges
        )
        for edge in edges:
            loads[edge] += volume

    utilization = {
        edge: loads[edge] / capacity_for(edge, active_scenario) for edge in EDGE_ORDER
    }
    overflow = sum(
        max(0.0, loads[edge] - capacity_for(edge, active_scenario))
        for edge in EDGE_ORDER
    )
    feasible = all(
        loads[edge] <= capacity_for(edge, active_scenario) + CAPACITY_TOLERANCE
        for edge in EDGE_ORDER
    )
    congestion = sum(value * value for value in utilization.values())

    return RawEvaluation(
        latency=total_latency,
        congestion=congestion,
        loads=MappingProxyType(loads),
        utilization=MappingProxyType(utilization),
        maximum_utilization=max(utilization.values(), default=0.0),
        overflow=overflow,
        feasible=feasible,
    )


def fit_normalizations() -> MappingProxyType:
    """Fit component ranges over all 81 one-hot assignments per scenario."""

    result: dict[str, ScenarioNormalization] = {}
    assignments = all_assignments()
    for scenario in SCENARIOS:
        raw = [raw_evaluate(assignment, scenario) for assignment in assignments]
        result[scenario.name] = ScenarioNormalization(
            latency=ComponentRange(
                min(item.latency for item in raw), max(item.latency for item in raw)
            ),
            congestion=ComponentRange(
                min(item.congestion for item in raw),
                max(item.congestion for item in raw),
            ),
        )
    return MappingProxyType(result)


def _normalize(value: float, component_range: ComponentRange) -> float:
    if isclose(component_range.span, 0.0, abs_tol=CAPACITY_TOLERANCE):
        return 0.0
    return (value - component_range.minimum) / component_range.span


class Evaluator:
    """Evaluate every solver output using identical frozen definitions."""

    def __init__(self) -> None:
        self.normalizations = fit_normalizations()
        self._regret_references: MappingProxyType | None = None

    def evaluate(
        self, assignment: Sequence[int], scenario: str | Scenario
    ) -> ScenarioEvaluation:
        active_scenario = _scenario(scenario)
        raw = raw_evaluate(assignment, active_scenario)
        normalizer = self.normalizations[active_scenario.name]
        normalized_latency = _normalize(raw.latency, normalizer.latency)
        normalized_congestion = _normalize(raw.congestion, normalizer.congestion)
        cost = (
            LATENCY_WEIGHT * normalized_latency
            + CONGESTION_WEIGHT * normalized_congestion
        )
        return ScenarioEvaluation(
            scenario=active_scenario.name,
            latency=raw.latency,
            congestion=raw.congestion,
            normalized_latency=normalized_latency,
            normalized_congestion=normalized_congestion,
            cost=cost,
            loads=raw.loads,
            utilization=raw.utilization,
            maximum_utilization=raw.maximum_utilization,
            overflow=raw.overflow,
            feasible=raw.feasible,
        )

    def evaluate_all(
        self, assignment: Sequence[int]
    ) -> tuple[ScenarioEvaluation, ...]:
        return tuple(self.evaluate(assignment, scenario) for scenario in SCENARIOS)

    def is_joint_feasible(self, assignment: Sequence[int]) -> bool:
        return all(item.feasible for item in self.evaluate_all(assignment))

    @property
    def regret_references(self) -> MappingProxyType:
        if self._regret_references is None:
            references: dict[str, RegretReference] = {}
            for scenario in SCENARIOS:
                feasible_costs = [
                    evaluation.cost
                    for assignment in all_assignments()
                    if (evaluation := self.evaluate(assignment, scenario)).feasible
                ]
                if not feasible_costs:
                    raise ValueError(f"scenario {scenario.name} has no feasible assignment")
                references[scenario.name] = RegretReference(
                    optimum=min(feasible_costs), maximum=max(feasible_costs)
                )
            self._regret_references = MappingProxyType(references)
        return self._regret_references

    def regret(self, assignment: Sequence[int], scenario: str | Scenario) -> float:
        active_scenario = _scenario(scenario)
        reference = self.regret_references[active_scenario.name]
        if isclose(reference.span, 0.0, abs_tol=CAPACITY_TOLERANCE):
            return 0.0
        return (
            self.evaluate(assignment, active_scenario).cost - reference.optimum
        ) / reference.span

    def weighted_objective(
        self,
        assignment: Sequence[int],
        weights: Sequence[float],
        mode: str,
    ) -> float:
        if len(weights) != len(SCENARIOS):
            raise ValueError("one weight is required per scenario")
        if mode == "cost":
            values = [self.evaluate(assignment, scenario).cost for scenario in SCENARIOS]
        elif mode == "regret":
            values = [self.regret(assignment, scenario) for scenario in SCENARIOS]
        else:
            raise ValueError(f"unsupported objective mode: {mode}")
        return sum(float(weight) * value for weight, value in zip(weights, values, strict=True))

    def joint_feasible_assignments(self) -> tuple[Assignment, ...]:
        return tuple(
            assignment
            for assignment in all_assignments()
            if self.is_joint_feasible(assignment)
        )
