"""Deterministic heuristic and matched random-sampling controls."""

from __future__ import annotations

import random
from collections import Counter
from typing import Sequence

import pandas as pd

from qera.evaluate import Evaluator, all_assignments
from qera.instance import DEMANDS, LINK_BY_EDGE, PATH_EDGES, SCENARIOS
from qera.qubo import bits_from_assignment
from qera.types import Assignment, BitState


def shortest_path_assignment() -> Assignment:
    """Choose each demand's lowest fixed-latency candidate independently."""

    choices = []
    for demand_index, _demand in enumerate(DEMANDS):
        path_latencies = [
            sum(LINK_BY_EDGE[edge].latency for edge in edges)
            for edges in PATH_EDGES[demand_index]
        ]
        choices.append(min(range(len(path_latencies)), key=path_latencies.__getitem__))
    return tuple(choices)  # type: ignore[return-value]


def load_aware_greedy(evaluator: Evaluator) -> Assignment:
    """Greedily minimize training overflow, max utilization, then uniform cost.

    Unassigned demands temporarily use their independent shortest path. This makes
    the heuristic deterministic and declares that all three training scenarios are
    visible to it.
    """

    fallback = shortest_path_assignment()
    chosen: list[int] = []
    uniform_weights = (1.0 / len(SCENARIOS),) * len(SCENARIOS)
    for demand_index in range(len(DEMANDS)):
        candidates = []
        for path_index in range(len(PATH_EDGES[demand_index])):
            trial = tuple(chosen + [path_index] + list(fallback[demand_index + 1 :]))
            evaluations = evaluator.evaluate_all(trial)
            score = (
                sum(item.overflow for item in evaluations),
                max(item.maximum_utilization for item in evaluations),
                evaluator.weighted_objective(trial, uniform_weights, "cost"),
                path_index,
            )
            candidates.append((score, path_index))
        chosen.append(min(candidates)[1])
    return tuple(chosen)  # type: ignore[return-value]


def random_bitstring_frame(shots: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    counts = Counter(
        tuple(rng.getrandbits(1) for _ in range(12)) for _ in range(shots)
    )
    return pd.DataFrame(
        {
            "routes": [list(bits) for bits in counts],
            "counts": list(counts.values()),
            "bitstring": ["".join(str(bit) for bit in bits) for bits in counts],
        }
    )


def random_valid_route_frame(shots: int, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    domain = all_assignments()
    counts = Counter(rng.choice(domain) for _ in range(shots))
    bitstates: list[BitState] = [bits_from_assignment(assignment) for assignment in counts]
    return pd.DataFrame(
        {
            "routes": [list(bits) for bits in bitstates],
            "counts": list(counts.values()),
            "bitstring": ["".join(str(bit) for bit in bits) for bits in bitstates],
        }
    )
