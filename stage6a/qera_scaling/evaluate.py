"""Variable-size evaluator preserving the frozen v1.1 formulas."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from itertools import product
from math import isclose
from time import perf_counter
from typing import Iterable, Sequence

from qera.config import CAPACITY_TOLERANCE, CONGESTION_WEIGHT, LATENCY_WEIGHT

from qera_scaling.model import Assignment, Edge, ScalingInstance, ScalingScenario


@dataclass(frozen=True)
class ComponentRange:
    minimum: float
    maximum: float

    @property
    def span(self) -> float:
        return self.maximum - self.minimum


@dataclass(frozen=True)
class Normalization:
    latency: ComponentRange
    congestion: ComponentRange


@dataclass(frozen=True)
class RawEvaluation:
    latency: float
    congestion: float
    loads: dict[Edge, float]
    utilization: dict[Edge, float]
    maximum_utilization: float
    overflow: float
    feasible: bool


@dataclass(frozen=True)
class Evaluation:
    scenario: str
    latency: float
    congestion: float
    normalized_latency: float
    normalized_congestion: float
    cost: float
    loads: dict[Edge, float]
    utilization: dict[Edge, float]
    maximum_utilization: float
    overflow: float
    feasible: bool


class ScalingEvaluator:
    """Evaluate any accepted Stage 6A instance with frozen formulas."""

    def __init__(self, instance: ScalingInstance) -> None:
        instance.validate_structure()
        self.instance = instance

    def all_assignments(self) -> Iterable[Assignment]:
        return product(
            range(self.instance.paths_per_demand),
            repeat=self.instance.demand_count,
        )

    def validate_assignment(self, assignment: Sequence[int]) -> Assignment:
        if len(assignment) != self.instance.demand_count:
            raise ValueError("assignment has the wrong demand count")
        result = tuple(int(value) for value in assignment)
        if any(
            value < 0 or value >= self.instance.paths_per_demand for value in result
        ):
            raise ValueError("assignment contains an invalid path index")
        return result

    def _scenario_index(self, scenario: str | ScalingScenario) -> int:
        name = scenario.name if isinstance(scenario, ScalingScenario) else scenario
        for index, item in enumerate(self.instance.scenarios):
            if item.name == name:
                return index
        raise ValueError(f"unknown scenario: {name}")

    @lru_cache(maxsize=None)
    def _raw_cached(self, route: Assignment, scenario_index: int) -> RawEvaluation:
        scenario = self.instance.scenarios[scenario_index]
        loads = {edge: 0.0 for edge in self.instance.edge_order}
        total_latency = 0.0
        paths = self.instance.path_edges
        links = self.instance.link_by_edge
        for demand_index, path_index in enumerate(route):
            demand = self.instance.demands[demand_index]
            volume = scenario.volumes[demand_index]
            edges = paths[demand_index][path_index]
            total_latency += volume * demand.priority * sum(
                links[edge].latency for edge in edges
            )
            for edge in edges:
                loads[edge] += volume
        utilization = {
            edge: loads[edge] / self.instance.capacity_for(edge, scenario)
            for edge in self.instance.edge_order
        }
        overflow = sum(
            max(0.0, loads[edge] - self.instance.capacity_for(edge, scenario))
            for edge in self.instance.edge_order
        )
        feasible = all(
            loads[edge]
            <= self.instance.capacity_for(edge, scenario) + CAPACITY_TOLERANCE
            for edge in self.instance.edge_order
        )
        return RawEvaluation(
            latency=total_latency,
            congestion=sum(value * value for value in utilization.values()),
            loads=loads,
            utilization=utilization,
            maximum_utilization=max(utilization.values(), default=0.0),
            overflow=overflow,
            feasible=feasible,
        )

    def raw_evaluate(
        self, assignment: Sequence[int], scenario: str | ScalingScenario
    ) -> RawEvaluation:
        return self._raw_cached(
            self.validate_assignment(assignment), self._scenario_index(scenario)
        )

    @cached_property
    def normalizations(self) -> dict[str, Normalization]:
        assignments = tuple(self.all_assignments())
        result = {}
        for scenario in self.instance.scenarios:
            values = [self.raw_evaluate(route, scenario) for route in assignments]
            result[scenario.name] = Normalization(
                latency=ComponentRange(
                    min(item.latency for item in values),
                    max(item.latency for item in values),
                ),
                congestion=ComponentRange(
                    min(item.congestion for item in values),
                    max(item.congestion for item in values),
                ),
            )
        return result

    @staticmethod
    def _normalize(value: float, span: ComponentRange) -> float:
        if isclose(span.span, 0.0, abs_tol=CAPACITY_TOLERANCE):
            return 0.0
        return (value - span.minimum) / span.span

    @lru_cache(maxsize=None)
    def _evaluate_cached(self, route: Assignment, scenario_index: int) -> Evaluation:
        scenario = self.instance.scenarios[scenario_index]
        raw = self._raw_cached(route, scenario_index)
        normalizer = self.normalizations[scenario.name]
        latency = self._normalize(raw.latency, normalizer.latency)
        congestion = self._normalize(raw.congestion, normalizer.congestion)
        return Evaluation(
            scenario=scenario.name,
            latency=raw.latency,
            congestion=raw.congestion,
            normalized_latency=latency,
            normalized_congestion=congestion,
            cost=LATENCY_WEIGHT * latency + CONGESTION_WEIGHT * congestion,
            loads=raw.loads,
            utilization=raw.utilization,
            maximum_utilization=raw.maximum_utilization,
            overflow=raw.overflow,
            feasible=raw.feasible,
        )

    def evaluate(
        self, assignment: Sequence[int], scenario: str | ScalingScenario
    ) -> Evaluation:
        return self._evaluate_cached(
            self.validate_assignment(assignment), self._scenario_index(scenario)
        )

    def evaluate_all(self, assignment: Sequence[int]) -> tuple[Evaluation, ...]:
        return tuple(self.evaluate(assignment, s) for s in self.instance.scenarios)

    def is_joint_feasible(self, assignment: Sequence[int]) -> bool:
        return all(item.feasible for item in self.evaluate_all(assignment))

    @cached_property
    def regret_references(self) -> dict[str, ComponentRange]:
        result = {}
        assignments = tuple(self.all_assignments())
        for scenario in self.instance.scenarios:
            feasible = [
                self.evaluate(route, scenario).cost
                for route in assignments
                if self.evaluate(route, scenario).feasible
            ]
            if not feasible:
                raise ValueError(f"scenario {scenario.name} has no feasible assignment")
            result[scenario.name] = ComponentRange(min(feasible), max(feasible))
        return result

    def regret(
        self, assignment: Sequence[int], scenario: str | ScalingScenario
    ) -> float:
        index = self._scenario_index(scenario)
        active = self.instance.scenarios[index]
        reference = self.regret_references[active.name]
        if isclose(reference.span, 0.0, abs_tol=CAPACITY_TOLERANCE):
            return 0.0
        return (self.evaluate(assignment, active).cost - reference.minimum) / reference.span

    def weighted_objective(
        self, assignment: Sequence[int], weights: Sequence[float], mode: str
    ) -> float:
        if len(weights) != self.instance.scenario_count:
            raise ValueError("one weight is required per scenario")
        if mode == "cost":
            values = [self.evaluate(assignment, s).cost for s in self.instance.scenarios]
        elif mode == "regret":
            values = [self.regret(assignment, s) for s in self.instance.scenarios]
        else:
            raise ValueError(f"unsupported objective mode: {mode}")
        return sum(float(w) * value for w, value in zip(weights, values, strict=True))

    def joint_feasible_assignments(self) -> tuple[Assignment, ...]:
        return tuple(route for route in self.all_assignments() if self.is_joint_feasible(route))

    def exact_optima(
        self, weights: Sequence[float], mode: str, *, joint_feasible: bool = True
    ) -> tuple[float, tuple[Assignment, ...], float]:
        start = perf_counter()
        domain = (
            self.joint_feasible_assignments()
            if joint_feasible
            else tuple(self.all_assignments())
        )
        scored = tuple((self.weighted_objective(route, weights, mode), route) for route in domain)
        minimum = min(value for value, _ in scored)
        ties = tuple(route for value, route in scored if isclose(value, minimum, abs_tol=1e-10))
        return minimum, ties, perf_counter() - start
