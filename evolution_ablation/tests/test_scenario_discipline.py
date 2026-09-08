from __future__ import annotations

import json
from collections import Counter

from holy_qow_evolution.common import artifact_root, implementation_root, sha256_file
from holy_qow_evolution.engine import ScenarioOracle
from holy_qow_evolution.scenarios import final_test_pool, training_pool, validation_pool


def test_pools_are_deterministic_diverse_and_disjoint() -> None:
    training = training_pool()
    validation = validation_pool()
    final = final_test_pool()
    assert (len(training), len(validation), len(final)) == (12, 16, 24)
    assert Counter(item.category for item in training)["combined"] >= 3
    assert Counter(item.category for item in validation) == {
        "demand": 4,
        "capacity": 4,
        "latency": 4,
        "combined": 4,
    }
    for left, right in ((training, validation), (training, final), (validation, final)):
        assert {item.scenario_id for item in left}.isdisjoint(item.scenario_id for item in right)
        assert {item.fingerprint() for item in left}.isdisjoint(item.fingerprint() for item in right)


def test_nested_training_domains_are_nonempty_and_no_link_is_removed() -> None:
    scenarios = training_pool()
    for size in (3, 5, 8, 12):
        assert ScenarioOracle(scenarios[:size]).joint_feasible_assignments()
    for scenario in (*scenarios, *validation_pool(), *final_test_pool()):
        assert all(value > 0.0 for value in scenario.capacity_multipliers.values())


def test_final_pool_is_loaded_from_immutable_post6a_manifest() -> None:
    path = implementation_root() / "artifacts" / "post6a" / "heldout" / "heldout_scenario_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert [item.scenario_id for item in final_test_pool()] == [item["scenario_id"] for item in manifest["scenarios"]]
    frozen = json.loads((artifact_root() / "manifests" / "evolution_scenario_manifests.json").read_text(encoding="utf-8"))
    assert frozen["frozen_final_source"]["sha256"] == sha256_file(path)
