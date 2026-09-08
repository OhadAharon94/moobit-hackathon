"""Frozen constants for the deterministic Q-ERA MVP fixture."""

from __future__ import annotations

SCHEMA_VERSION = "1.0"
PLAN_VERSION = "1.1"

DEMAND_COUNT = 4
PATHS_PER_DEMAND = 3
VARIABLE_COUNT = DEMAND_COUNT * PATHS_PER_DEMAND
SCENARIO_ORDER = ("nominal", "surge", "degradation")

LATENCY_WEIGHT = 0.4
CONGESTION_WEIGHT = 0.6
CAPACITY_TOLERANCE = 1e-9
ENERGY_TOLERANCE = 1e-8

ADAPTIVE_SOLVES = 3
ADAPTIVE_ETA = 1.0
INITIAL_SCENARIO_WEIGHTS = (1.0 / 3.0,) * 3

QAOA_DEPTH = 1
OPTIMIZER_ITERATIONS = 40
OPTIMIZER_SHOTS = 512
FINAL_SHOTS = 4096
OPTIMIZER_QUANTILE = 1.0
DEFAULT_SEED = 1701


def variable_index(demand_index: int, path_index: int) -> int:
    """Return the canonical binary-variable index i = 3*d + p."""

    if not 0 <= demand_index < DEMAND_COUNT:
        raise ValueError(f"invalid demand index: {demand_index}")
    if not 0 <= path_index < PATHS_PER_DEMAND:
        raise ValueError(f"invalid path index: {path_index}")
    return PATHS_PER_DEMAND * demand_index + path_index

