"""Deterministic directed-network fixture for the Q-ERA MVP."""

from __future__ import annotations

from itertools import pairwise
from types import MappingProxyType

from qera.config import DEMAND_COUNT, PATHS_PER_DEMAND, SCENARIO_ORDER
from qera.types import Demand, Edge, Link, Scenario

LINKS = (
    Link(("S0", "U"), 1.0, 10.0),
    Link(("S0", "L"), 1.5, 10.0),
    Link(("S1", "U"), 1.0, 10.0),
    Link(("S1", "L"), 1.5, 10.0),
    Link(("U", "M1"), 1.0, 6.0),
    Link(("U", "M2"), 2.5, 5.0),
    Link(("L", "M1"), 2.5, 5.0),
    Link(("L", "M2"), 1.2, 6.0),
    Link(("M1", "T0"), 1.0, 10.0),
    Link(("M1", "T1"), 1.0, 10.0),
    Link(("M2", "T0"), 1.2, 10.0),
    Link(("M2", "T1"), 1.2, 10.0),
)

LINK_BY_EDGE = MappingProxyType({link.edge: link for link in LINKS})
EDGE_ORDER = tuple(link.edge for link in LINKS)

DEMANDS = (
    Demand(
        "d0",
        "S0",
        "T0",
        1.0,
        (
            ("S0", "U", "M1", "T0"),
            ("S0", "L", "M2", "T0"),
            ("S0", "U", "M2", "T0"),
        ),
    ),
    Demand(
        "d1",
        "S0",
        "T1",
        1.0,
        (
            ("S0", "U", "M1", "T1"),
            ("S0", "L", "M2", "T1"),
            ("S0", "L", "M1", "T1"),
        ),
    ),
    Demand(
        "d2",
        "S1",
        "T0",
        1.0,
        (
            ("S1", "U", "M1", "T0"),
            ("S1", "L", "M2", "T0"),
            ("S1", "L", "M1", "T0"),
        ),
    ),
    Demand(
        "d3",
        "S1",
        "T1",
        1.0,
        (
            ("S1", "U", "M1", "T1"),
            ("S1", "L", "M2", "T1"),
            ("S1", "U", "M2", "T1"),
        ),
    ),
)

SCENARIOS = (
    Scenario("nominal", (2.0, 2.0, 2.0, 2.0)),
    Scenario("surge", (3.0, 3.0, 2.0, 2.0)),
    Scenario(
        "degradation",
        (2.0, 2.0, 2.0, 2.0),
        MappingProxyType({("U", "M1"): 2.0}),
    ),
)

SCENARIO_BY_NAME = MappingProxyType({scenario.name: scenario for scenario in SCENARIOS})


def path_edges(nodes: tuple[str, ...]) -> tuple[Edge, ...]:
    """Convert an ordered node path into directed edges."""

    return tuple(pairwise(nodes))


PATH_EDGES = tuple(
    tuple(path_edges(path) for path in demand.paths) for demand in DEMANDS
)


def capacity_for(edge: Edge, scenario: Scenario) -> float:
    """Return the scenario capacity for a link."""

    return float(scenario.capacity_overrides.get(edge, LINK_BY_EDGE[edge].nominal_capacity))


def validate_fixture() -> None:
    """Fail fast if the frozen fixture violates its structural contract."""

    if len(DEMANDS) != DEMAND_COUNT:
        raise ValueError("fixture demand count does not match frozen config")
    if tuple(s.name for s in SCENARIOS) != SCENARIO_ORDER:
        raise ValueError("scenario order does not match frozen config")
    for demand_index, demand in enumerate(DEMANDS):
        if len(demand.paths) != PATHS_PER_DEMAND:
            raise ValueError(f"demand {demand.name} must have three paths")
        for path_index, nodes in enumerate(demand.paths):
            if nodes[0] != demand.source or nodes[-1] != demand.target:
                raise ValueError(
                    f"path ({demand_index}, {path_index}) has wrong endpoints"
                )
            missing = [edge for edge in path_edges(nodes) if edge not in LINK_BY_EDGE]
            if missing:
                raise ValueError(
                    f"path ({demand_index}, {path_index}) has missing edges: {missing}"
                )


validate_fixture()
