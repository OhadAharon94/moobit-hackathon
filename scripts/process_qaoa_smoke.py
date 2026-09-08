"""Decode and evaluate the saved Stage 3 Classiq sample distribution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from qera.classiq_solver import process_sample_frame
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", default="uniform_cost_p1_smoke")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    implementation_root = Path(__file__).resolve().parents[1]
    run_dir = implementation_root / "artifacts" / "runs" / args.run_name
    manifest_path = run_dir / "manifest.json"
    raw_path = run_dir / "samples_raw.csv"
    if not manifest_path.exists() or not raw_path.exists():
        raise FileNotFoundError("run execute_qaoa_smoke.py before post-processing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    evaluator = Evaluator()
    spec = build_energy_spec(
        evaluator,
        manifest["scenario_weights"],
        manifest["objective_mode"],
        manifest["energy_mode"],
    )
    processed, summary = process_sample_frame(
        pd.read_csv(raw_path, dtype={"bitstring": "string"}),
        evaluator,
        spec,
        manifest["scenario_weights"],
        manifest["objective_mode"],
        declared_shots=manifest["final_shots"],
    )
    processed.to_csv(run_dir / "samples.csv", index=False)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest["status"] = summary["status"]
    manifest["summary_path"] = str((run_dir / "summary.json").resolve())
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(run_dir.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
