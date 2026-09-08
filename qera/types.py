"""Shared immutable data contracts for Q-ERA."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence

Edge = tuple[str, str]
Assignment = tuple[int, int, int, int]
BitState = tuple[int, ...]


@dataclass(frozen=True)
class Link:
    edge: Edge
    latency: float
    nominal_capacity: float


@dataclass(frozen=True)
class Demand:
    name: str
    source: str
    target: str
    priority: float
    paths: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Scenario:
    name: str
    volumes: tuple[float, ...]
    capacity_overrides: Mapping[Edge, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ComponentRange:
    minimum: float
    maximum: float

    @property
    def span(self) -> float:
        return self.maximum - self.minimum


@dataclass(frozen=True)
class ScenarioNormalization:
    latency: ComponentRange
    congestion: ComponentRange


@dataclass(frozen=True)
class ScenarioEvaluation:
    scenario: str
    latency: float
    congestion: float
    normalized_latency: float
    normalized_congestion: float
    cost: float
    loads: Mapping[Edge, float]
    utilization: Mapping[Edge, float]
    maximum_utilization: float
    overflow: float
    feasible: bool


@dataclass(frozen=True)
class RegretReference:
    optimum: float
    maximum: float

    @property
    def span(self) -> float:
        return self.maximum - self.optimum


@dataclass(frozen=True)
class QuboModel:
    offset: float
    linear: tuple[float, ...]
    quadratic: Mapping[tuple[int, int], float]
    one_hot_penalty: float
    variable_map: Mapping[int, tuple[int, int]]
    verification_summary: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IsingModel:
    offset: float
    linear: tuple[float, ...]
    quadratic: Mapping[tuple[int, int], float]


class SolveStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NO_FEASIBLE_SAMPLE = "NO_FEASIBLE_SAMPLE"
    SYNTHESIS_FAILED = "SYNTHESIS_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    EXECUTION_FAILED = "EXECUTION_FAILED"


@dataclass(frozen=True)
class SolveRequest:
    objective_mode: str
    scenario_weights: tuple[float, ...]
    energy_mode: str = "base"
    seed: int = 1701


@dataclass
class SolveResult:
    status: SolveStatus
    assignment: Assignment | None
    objective_value: float | None
    raw_candidates: list[Mapping[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

