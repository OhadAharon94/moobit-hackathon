"""Immutable, variable-size data contracts for Stage 6A."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise
from typing import Mapping

Edge = tuple[str, str]
Assignment = tuple[int, ...]
BitState = tuple[int, ...]


@dataclass(frozen=True)
class ScalingLink:
    edge: Edge
    latency: float
    nominal_capacity: float


@dataclass(frozen=True)
class ScalingDemand:
    name: str
    source: str
    target: str
    priority: float
    paths: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ScalingScenario:
    name: str
    volumes: tuple[float, ...]
    capacity_overrides: Mapping[Edge, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScalingInstance:
    instance_id: str
    seed: int
    links: tuple[ScalingLink, ...]
    demands: tuple[ScalingDemand, ...]
    scenarios: tuple[ScalingScenario, ...]

    @property
    def demand_count(self) -> int:
        return len(self.demands)

    @property
    def paths_per_demand(self) -> int:
        return len(self.demands[0].paths)

    @property
    def scenario_count(self) -> int:
        return len(self.scenarios)

    @property
    def variable_count(self) -> int:
        return self.demand_count * self.paths_per_demand

    @property
    def edge_order(self) -> tuple[Edge, ...]:
        return tuple(link.edge for link in self.links)

    @property
    def link_by_edge(self) -> dict[Edge, ScalingLink]:
        return {link.edge: link for link in self.links}

    @property
    def path_edges(self) -> tuple[tuple[tuple[Edge, ...], ...], ...]:
        return tuple(
            tuple(tuple(pairwise(path)) for path in demand.paths)
            for demand in self.demands
        )

    def capacity_for(self, edge: Edge, scenario: ScalingScenario) -> float:
        return float(
            scenario.capacity_overrides.get(
                edge, self.link_by_edge[edge].nominal_capacity
            )
        )

    def variable_index(self, demand_index: int, path_index: int) -> int:
        if not 0 <= demand_index < self.demand_count:
            raise ValueError(f"invalid demand index: {demand_index}")
        if not 0 <= path_index < self.paths_per_demand:
            raise ValueError(f"invalid path index: {path_index}")
        return self.paths_per_demand * demand_index + path_index

    def validate_structure(self) -> None:
        if self.paths_per_demand != 3:
            raise ValueError("Stage 6A core requires K=3")
        if self.scenario_count != 3:
            raise ValueError("Stage 6A core requires S=3")
        if tuple(s.name for s in self.scenarios) != (
            "nominal",
            "surge",
            "degradation",
        ):
            raise ValueError("scenario order must match frozen v1.1")
        links = self.link_by_edge
        for scenario in self.scenarios:
            if len(scenario.volumes) != self.demand_count:
                raise ValueError(f"scenario {scenario.name} has the wrong volume count")
            if any(edge not in links for edge in scenario.capacity_overrides):
                raise ValueError(f"scenario {scenario.name} overrides an unknown edge")
        for demand in self.demands:
            if len(demand.paths) != 3 or len(set(demand.paths)) != 3:
                raise ValueError(f"demand {demand.name} needs three distinct paths")
            for path in demand.paths:
                if path[0] != demand.source or path[-1] != demand.target:
                    raise ValueError(f"demand {demand.name} has a path with wrong endpoints")
                if len(path) != len(set(path)):
                    raise ValueError(f"demand {demand.name} has a non-simple path")
                missing = [edge for edge in pairwise(path) if edge not in links]
                if missing:
                    raise ValueError(f"demand {demand.name} path has missing edges: {missing}")

    def to_dict(self) -> dict:
        nodes = sorted({node for link in self.links for node in link.edge})
        return {
            "instance_id": self.instance_id,
            "seed": self.seed,
            "D": self.demand_count,
            "K": self.paths_per_demand,
            "S": self.scenario_count,
            "nodes": nodes,
            "edges": [
                {
                    "source": link.edge[0],
                    "target": link.edge[1],
                    "latency": link.latency,
                    "nominal_capacity": link.nominal_capacity,
                }
                for link in self.links
            ],
            "capacities": {
                f"{link.edge[0]}->{link.edge[1]}": link.nominal_capacity
                for link in self.links
            },
            "latencies": {
                f"{link.edge[0]}->{link.edge[1]}": link.latency
                for link in self.links
            },
            "demands": [
                {
                    "name": demand.name,
                    "source": demand.source,
                    "target": demand.target,
                    "priority": demand.priority,
                    "candidate_paths": [list(path) for path in demand.paths],
                }
                for demand in self.demands
            ],
            "candidate_paths": {
                demand.name: [list(path) for path in demand.paths]
                for demand in self.demands
            },
            "scenario_parameters": [
                {
                    "name": scenario.name,
                    "volumes": list(scenario.volumes),
                    "capacity_overrides": {
                        f"{edge[0]}->{edge[1]}": value
                        for edge, value in scenario.capacity_overrides.items()
                    },
                }
                for scenario in self.scenarios
            ],
        }
