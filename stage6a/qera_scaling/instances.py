"""Deterministic Stage 6A instance construction."""

from __future__ import annotations

import random

from qera.instance import DEMANDS, LINKS, SCENARIOS

from qera_scaling.model import (
    ScalingDemand,
    ScalingInstance,
    ScalingLink,
    ScalingScenario,
)

CORE_SIZES = (4, 5, 6, 8)
SEED_BASE = 6100


def frozen_instance() -> ScalingInstance:
    """Adapt the v1.1 fixture without changing any scientific value."""

    instance = ScalingInstance(
        instance_id="qera-d4-frozen",
        seed=1701,
        links=tuple(
            ScalingLink(link.edge, link.latency, link.nominal_capacity)
            for link in LINKS
        ),
        demands=tuple(
            ScalingDemand(
                demand.name,
                demand.source,
                demand.target,
                demand.priority,
                demand.paths,
            )
            for demand in DEMANDS
        ),
        scenarios=tuple(
            ScalingScenario(
                scenario.name,
                scenario.volumes,
                dict(scenario.capacity_overrides),
            )
            for scenario in SCENARIOS
        ),
    )
    instance.validate_structure()
    return instance


def generate_instance(demand_count: int, seed: int | None = None) -> ScalingInstance:
    """Extend the frozen two-corridor motif with deterministic repeated OD pairs."""

    if demand_count == 4:
        return frozen_instance()
    if demand_count < 4:
        raise ValueError("Stage 6A instances start at D=4")
    selected_seed = SEED_BASE + demand_count if seed is None else int(seed)
    rng = random.Random(selected_seed)
    scale = demand_count / 4.0
    links = (
        ScalingLink(("S0", "U"), 1.0, max(10.0, 2.5 * demand_count)),
        ScalingLink(("S0", "L"), 1.5, max(10.0, 2.5 * demand_count)),
        ScalingLink(("S1", "U"), 1.0, max(10.0, 2.5 * demand_count)),
        ScalingLink(("S1", "L"), 1.5, max(10.0, 2.5 * demand_count)),
        ScalingLink(("U", "M1"), 1.0, round(6.0 * scale, 6)),
        ScalingLink(("U", "M2"), 2.5, round(5.0 * scale, 6)),
        ScalingLink(("L", "M1"), 2.5, round(5.0 * scale, 6)),
        ScalingLink(("L", "M2"), 1.2, round(6.0 * scale, 6)),
        ScalingLink(("M1", "T0"), 1.0, max(10.0, 2.5 * demand_count)),
        ScalingLink(("M1", "T1"), 1.0, max(10.0, 2.5 * demand_count)),
        ScalingLink(("M2", "T0"), 1.2, max(10.0, 2.5 * demand_count)),
        ScalingLink(("M2", "T1"), 1.2, max(10.0, 2.5 * demand_count)),
    )
    patterns = (
        ("S0", "T0", "U", "M2"),
        ("S0", "T1", "L", "M1"),
        ("S1", "T0", "L", "M1"),
        ("S1", "T1", "U", "M2"),
    )
    demands = []
    for index in range(demand_count):
        source, target, cross_entry, cross_middle = patterns[index % len(patterns)]
        priority = 1.0 + rng.choice((-0.08, 0.0, 0.08))
        demands.append(
            ScalingDemand(
                name=f"d{index}",
                source=source,
                target=target,
                priority=priority,
                paths=(
                    (source, "U", "M1", target),
                    (source, "L", "M2", target),
                    (source, cross_entry, cross_middle, target),
                ),
            )
        )
    surge_count = (demand_count + 1) // 2
    scenarios = (
        ScalingScenario("nominal", (2.0,) * demand_count),
        ScalingScenario(
            "surge",
            tuple(3.0 if index < surge_count else 2.0 for index in range(demand_count)),
        ),
        ScalingScenario(
            "degradation",
            (2.0,) * demand_count,
            {("U", "M1"): round(2.0 * scale, 6)},
        ),
    )
    instance = ScalingInstance(
        instance_id=f"qera-d{demand_count}-seed{selected_seed}",
        seed=selected_seed,
        links=links,
        demands=tuple(demands),
        scenarios=scenarios,
    )
    instance.validate_structure()
    return instance


def core_instances() -> tuple[ScalingInstance, ...]:
    return tuple(generate_instance(size) for size in CORE_SIZES)
