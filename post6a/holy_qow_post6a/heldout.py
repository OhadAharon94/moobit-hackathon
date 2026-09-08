"""Deterministic held-out perturbations evaluated by the validated scaling evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import frozen_instance
from qera_scaling.model import ScalingInstance, ScalingLink, ScalingScenario

from holy_qow_post6a.common import implementation_root, sha256_file

Edge = tuple[str, str]


@dataclass(frozen=True)
class HeldoutScenario:
    scenario_id: str
    category: str
    description: str
    demand_multipliers: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    capacity_multipliers: Mapping[Edge, float] = field(default_factory=dict)
    latency_multipliers: Mapping[Edge, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        def edges(values: Mapping[Edge, float]) -> dict[str, float]:
            return {f"{edge[0]}->{edge[1]}": value for edge, value in values.items()}

        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "description": self.description,
            "demand_multipliers": list(self.demand_multipliers),
            "capacity_multipliers": edges(self.capacity_multipliers),
            "latency_multipliers": edges(self.latency_multipliers),
        }


def heldout_scenarios() -> tuple[HeldoutScenario, ...]:
    u_m1 = ("U", "M1")
    l_m2 = ("L", "M2")
    u_m2 = ("U", "M2")
    return (
        HeldoutScenario("demand-all-10", "demand", "All demands +10%", (1.1,) * 4),
        HeldoutScenario("demand-all-20", "demand", "All demands +20%", (1.2,) * 4),
        HeldoutScenario("demand-all-30", "demand", "All demands +30%", (1.3,) * 4),
        HeldoutScenario("demand-s0-20", "demand", "S0-origin demands +20%", (1.2, 1.2, 1.0, 1.0)),
        HeldoutScenario("demand-s0-30", "demand", "S0-origin demands +30%", (1.3, 1.3, 1.0, 1.0)),
        HeldoutScenario("demand-s1-30", "demand", "S1-origin demands +30%", (1.0, 1.0, 1.3, 1.3)),
        HeldoutScenario("capacity-um1-10", "capacity", "U-M1 capacity -10%", capacity_multipliers={u_m1: 0.9}),
        HeldoutScenario("capacity-um1-20", "capacity", "U-M1 capacity -20%", capacity_multipliers={u_m1: 0.8}),
        HeldoutScenario("capacity-um1-30", "capacity", "U-M1 capacity -30%", capacity_multipliers={u_m1: 0.7}),
        HeldoutScenario("capacity-um1-40", "capacity", "U-M1 capacity -40%", capacity_multipliers={u_m1: 0.6}),
        HeldoutScenario("capacity-lm2-20", "capacity", "L-M2 capacity -20%", capacity_multipliers={l_m2: 0.8}),
        HeldoutScenario("capacity-lm2-40", "capacity", "L-M2 capacity -40%", capacity_multipliers={l_m2: 0.6}),
        HeldoutScenario("latency-um1-10", "latency", "U-M1 latency +10%", latency_multipliers={u_m1: 1.1}),
        HeldoutScenario("latency-um1-25", "latency", "U-M1 latency +25%", latency_multipliers={u_m1: 1.25}),
        HeldoutScenario("latency-um1-50", "latency", "U-M1 latency +50%", latency_multipliers={u_m1: 1.5}),
        HeldoutScenario("latency-lm2-25", "latency", "L-M2 latency +25%", latency_multipliers={l_m2: 1.25}),
        HeldoutScenario("latency-lm2-50", "latency", "L-M2 latency +50%", latency_multipliers={l_m2: 1.5}),
        HeldoutScenario("latency-um2-50", "latency", "U-M2 latency +50%", latency_multipliers={u_m2: 1.5}),
        HeldoutScenario(
            "combined-all20-um1cap20",
            "combined",
            "All demands +20%; U-M1 capacity -20%",
            (1.2,) * 4,
            {u_m1: 0.8},
        ),
        HeldoutScenario(
            "combined-s030-um1cap30",
            "combined",
            "S0 demands +30%; U-M1 capacity -30%",
            (1.3, 1.3, 1.0, 1.0),
            {u_m1: 0.7},
        ),
        HeldoutScenario(
            "combined-s130-lm2cap30",
            "combined",
            "S1 demands +30%; L-M2 capacity -30%",
            (1.0, 1.0, 1.3, 1.3),
            {l_m2: 0.7},
        ),
        HeldoutScenario(
            "combined-all10-um1lat50",
            "combined",
            "All demands +10%; U-M1 latency +50%",
            (1.1,) * 4,
            latency_multipliers={u_m1: 1.5},
        ),
        HeldoutScenario(
            "combined-s020-lm2lat25",
            "combined",
            "S0 demands +20%; L-M2 latency +25%",
            (1.2, 1.2, 1.0, 1.0),
            latency_multipliers={l_m2: 1.25},
        ),
        HeldoutScenario(
            "combined-all20-um1cap20-lm2lat25",
            "combined",
            "All demands +20%; U-M1 capacity -20%; L-M2 latency +25%",
            (1.2,) * 4,
            {u_m1: 0.8},
            {l_m2: 1.25},
        ),
    )


def build_evaluator(spec: HeldoutScenario) -> ScalingEvaluator:
    base = frozen_instance()
    links = tuple(
        ScalingLink(
            link.edge,
            link.latency * float(spec.latency_multipliers.get(link.edge, 1.0)),
            link.nominal_capacity,
        )
        for link in base.links
    )
    volumes = tuple(
        2.0 * multiplier for multiplier in spec.demand_multipliers
    )
    overrides = {
        edge: base.link_by_edge[edge].nominal_capacity * float(multiplier)
        for edge, multiplier in spec.capacity_multipliers.items()
    }
    scenarios = tuple(
        ScalingScenario(name, volumes, overrides)
        for name in ("nominal", "surge", "degradation")
    )
    instance = ScalingInstance(
        instance_id=f"holy-qow-heldout-{spec.scenario_id}",
        seed=7600,
        links=links,
        demands=base.demands,
        scenarios=scenarios,
    )
    return ScalingEvaluator(instance)


def route_manifest() -> dict:
    root = implementation_root()
    exact_path = root / "artifacts" / "tables" / "exact_truth.json"
    qaoa_path = root / "artifacts" / "runs" / "adaptive_cost" / "summary.json"
    import json

    exact = json.loads(exact_path.read_text(encoding="utf-8"))
    qaoa = json.loads(qaoa_path.read_text(encoding="utf-8"))
    routes = [
        {
            "route_id": "nominal_only",
            "assignment": exact["scenarios"]["nominal"]["optimum_assignments"][0],
            "source": "deterministic first representative of the frozen nominal optimum tie",
        },
        {
            "route_id": "static_uniform_multiscenario",
            "assignment": exact["uniform_joint_cost"]["assignments"][0],
            "source": "frozen exact static uniform multi-scenario optimum",
        },
        {
            "route_id": "exact_adaptive",
            "assignment": exact["adaptive_cost"][-1]["assignment"],
            "source": "frozen exact-inner adaptive cost trajectory final route",
        },
        {
            "route_id": "qaoa_adaptive",
            "assignment": qaoa["best_assignment"],
            "source": "completed MVP saved-QAOA adaptive run best route",
        },
        {
            "route_id": "exact_pure_minimax",
            "assignment": exact["pure_minimax_regret"]["assignments"][0],
            "source": "deterministic first representative of the frozen minimax tie",
        },
    ]
    return {
        "schema_version": "post6a-steps0-2-v1",
        "selection_policy": "all route identities fixed from pre-held-out artifacts",
        "routes": routes,
        "source_artifacts": [
            {"path": str(exact_path.resolve()), "sha256": sha256_file(exact_path)},
            {"path": str(qaoa_path.resolve()), "sha256": sha256_file(qaoa_path)},
        ],
    }
