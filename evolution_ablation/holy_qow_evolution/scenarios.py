"""Deterministic, non-overlapping scenario pools for Track B."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import json

from holy_qow_post6a.heldout import HeldoutScenario, build_evaluator

from holy_qow_evolution.common import implementation_root, sha256_payload

Edge = tuple[str, str]


@dataclass(frozen=True)
class ExperimentScenario:
    scenario_id: str
    category: str
    description: str
    demand_multipliers: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    capacity_multipliers: Mapping[Edge, float] = field(default_factory=dict)
    latency_multipliers: Mapping[Edge, float] = field(default_factory=dict)

    def as_heldout(self) -> HeldoutScenario:
        return HeldoutScenario(
            self.scenario_id,
            self.category,
            self.description,
            self.demand_multipliers,
            dict(self.capacity_multipliers),
            dict(self.latency_multipliers),
        )

    def parameter_payload(self) -> dict:
        def edge_map(values: Mapping[Edge, float]) -> dict[str, float]:
            return {
                f"{edge[0]}->{edge[1]}": float(value)
                for edge, value in sorted(values.items())
            }

        return {
            "demand_multipliers": [float(value) for value in self.demand_multipliers],
            "capacity_multipliers": edge_map(self.capacity_multipliers),
            "latency_multipliers": edge_map(self.latency_multipliers),
        }

    def fingerprint(self) -> str:
        return sha256_payload(self.parameter_payload())

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "description": self.description,
            **self.parameter_payload(),
            "fingerprint": self.fingerprint(),
            "feasible_assignment_count": len(build_evaluator(self.as_heldout()).joint_feasible_assignments()),
        }


def original_training_pool() -> tuple[ExperimentScenario, ...]:
    """The frozen S=3 training set expressed as perturbations of D=4 nominal."""

    return (
        ExperimentScenario("train-original-nominal", "nominal", "Frozen nominal"),
        ExperimentScenario(
            "train-original-surge-s0-50",
            "demand",
            "Frozen surge: S0-origin demands +50%",
            (1.5, 1.5, 1.0, 1.0),
        ),
        ExperimentScenario(
            "train-original-degradation-um1",
            "capacity",
            "Frozen degradation: U-M1 capacity from 6 to 2",
            capacity_multipliers={("U", "M1"): 1.0 / 3.0},
        ),
    )


def training_pool() -> tuple[ExperimentScenario, ...]:
    """Nested S={3,5,8,12} pool; the first three are exactly frozen."""

    u_m1 = ("U", "M1")
    u_m2 = ("U", "M2")
    l_m1 = ("L", "M1")
    l_m2 = ("L", "M2")
    return original_training_pool() + (
        ExperimentScenario(
            "train-demand-s1-25", "demand", "S1-origin demands +25%", (1.0, 1.0, 1.25, 1.25)
        ),
        ExperimentScenario(
            "train-capacity-lm2-25", "capacity", "L-M2 capacity -25%", capacity_multipliers={l_m2: 0.75}
        ),
        ExperimentScenario(
            "train-latency-um1-35", "latency", "U-M1 latency +35%", latency_multipliers={u_m1: 1.35}
        ),
        ExperimentScenario(
            "train-combined-all12-lm2cap18",
            "combined",
            "All demands +12%; L-M2 capacity -18%",
            (1.12, 1.12, 1.12, 1.12),
            {l_m2: 0.82},
        ),
        ExperimentScenario(
            "train-demand-alternating-30",
            "demand",
            "Demands d0 and d2 +30%",
            (1.3, 1.0, 1.3, 1.0),
        ),
        ExperimentScenario(
            "train-capacity-um2-30", "capacity", "U-M2 capacity -30%", capacity_multipliers={u_m2: 0.7}
        ),
        ExperimentScenario(
            "train-latency-lm1-40", "latency", "L-M1 latency +40%", latency_multipliers={l_m1: 1.4}
        ),
        ExperimentScenario(
            "train-combined-s0-22-um1cap17",
            "combined",
            "S0-origin demands +22%; U-M1 capacity -17%",
            (1.22, 1.22, 1.0, 1.0),
            {u_m1: 0.83},
        ),
        ExperimentScenario(
            "train-combined-s1-18-lm2lat30",
            "combined",
            "S1-origin demands +18%; L-M2 latency +30%",
            (1.0, 1.0, 1.18, 1.18),
            latency_multipliers={l_m2: 1.3},
        ),
    )


def validation_pool() -> tuple[ExperimentScenario, ...]:
    """Sixteen scenarios reserved for validation-based configuration selection."""

    u_m1 = ("U", "M1")
    u_m2 = ("U", "M2")
    l_m1 = ("L", "M1")
    l_m2 = ("L", "M2")
    return (
        ExperimentScenario("val-demand-all-15", "demand", "All demands +15%", (1.15,) * 4),
        ExperimentScenario("val-demand-s0-18", "demand", "S0-origin demands +18%", (1.18, 1.18, 1.0, 1.0)),
        ExperimentScenario("val-demand-s1-22", "demand", "S1-origin demands +22%", (1.0, 1.0, 1.22, 1.22)),
        ExperimentScenario("val-demand-alternating-25", "demand", "Demands d0 and d2 +25%", (1.25, 1.0, 1.25, 1.0)),
        ExperimentScenario("val-capacity-um1-15", "capacity", "U-M1 capacity -15%", capacity_multipliers={u_m1: 0.85}),
        ExperimentScenario("val-capacity-lm2-15", "capacity", "L-M2 capacity -15%", capacity_multipliers={l_m2: 0.85}),
        ExperimentScenario("val-capacity-um2-25", "capacity", "U-M2 capacity -25%", capacity_multipliers={u_m2: 0.75}),
        ExperimentScenario("val-capacity-lm1-20", "capacity", "L-M1 capacity -20%", capacity_multipliers={l_m1: 0.8}),
        ExperimentScenario("val-latency-um1-20", "latency", "U-M1 latency +20%", latency_multipliers={u_m1: 1.2}),
        ExperimentScenario("val-latency-lm2-20", "latency", "L-M2 latency +20%", latency_multipliers={l_m2: 1.2}),
        ExperimentScenario("val-latency-um2-30", "latency", "U-M2 latency +30%", latency_multipliers={u_m2: 1.3}),
        ExperimentScenario("val-latency-lm1-45", "latency", "L-M1 latency +45%", latency_multipliers={l_m1: 1.45}),
        ExperimentScenario("val-combined-all15-um1cap12", "combined", "All demands +15%; U-M1 capacity -12%", (1.15,) * 4, {u_m1: 0.88}),
        ExperimentScenario("val-combined-s0-17-lm2lat35", "combined", "S0 demands +17%; L-M2 latency +35%", (1.17, 1.17, 1.0, 1.0), latency_multipliers={l_m2: 1.35}),
        ExperimentScenario("val-combined-s1-24-lm2cap18", "combined", "S1 demands +24%; L-M2 capacity -18%", (1.0, 1.0, 1.24, 1.24), {l_m2: 0.82}),
        ExperimentScenario("val-combined-alt20-um2lat35", "combined", "d0/d2 +20%; U-M2 latency +35%", (1.2, 1.0, 1.2, 1.0), latency_multipliers={u_m2: 1.35}),
    )


def final_test_pool() -> tuple[ExperimentScenario, ...]:
    """Load the immutable 24-case Post-6A manifest, not a regenerated copy."""

    path = (
        implementation_root()
        / "artifacts"
        / "post6a"
        / "heldout"
        / "heldout_scenario_manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))

    def edges(values: Mapping[str, float]) -> dict[Edge, float]:
        return {
            tuple(name.split("->", maxsplit=1)): float(value)  # type: ignore[misc]
            for name, value in values.items()
        }

    return tuple(
        ExperimentScenario(
            item["scenario_id"],
            item["category"],
            item["description"],
            tuple(float(value) for value in item["demand_multipliers"]),  # type: ignore[arg-type]
            edges(item["capacity_multipliers"]),
            edges(item["latency_multipliers"]),
        )
        for item in manifest["scenarios"]
    )
