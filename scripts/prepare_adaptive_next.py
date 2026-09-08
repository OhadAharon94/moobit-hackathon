"""Compute the next adaptive weights and a scale-corrected p=1 warm start."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.exact import update_weights
from qera.instance import SCENARIOS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-run", required=True)
    parser.add_argument("--next-name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    implementation_root = Path(__file__).resolve().parents[1]
    previous_dir = implementation_root / "artifacts" / "runs" / args.previous_run
    manifest = json.loads((previous_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((previous_dir / "summary.json").read_text(encoding="utf-8"))
    assignment = tuple(summary["selected_assignment"])
    evaluator = Evaluator()
    regrets = tuple(evaluator.regret(assignment, scenario) for scenario in SCENARIOS)
    new_weights = update_weights(manifest["scenario_weights"], regrets)
    new_spec = build_energy_spec(
        evaluator, new_weights, manifest["objective_mode"], manifest["energy_mode"]
    )
    old_params = manifest["best_parameters"]["params"]
    old_scale = manifest["phase_scale"]
    warm_start = [old_params[0] * new_spec.phase_scale / old_scale, old_params[1]]
    payload = {
        "previous_run": args.previous_run,
        "next_name": args.next_name,
        "selected_assignment": assignment,
        "regrets": regrets,
        "weights": new_weights,
        "previous_phase_scale": old_scale,
        "next_phase_scale": new_spec.phase_scale,
        "previous_parameters": old_params,
        "warm_start_parameters": warm_start,
    }
    output = implementation_root / "artifacts" / "runs" / f"{args.next_name}.prepared.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output.resolve())
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
