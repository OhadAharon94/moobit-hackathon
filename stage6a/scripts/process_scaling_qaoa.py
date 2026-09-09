"""Post-process one saved Stage 6A QAOA run and matched controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.postprocess import (
    process_sample_frame,
    random_bitstring_frame,
    random_valid_route_frame,
)
from qera_scaling.provenance import (
    sha256_file,
    validate_scaling_circuit_manifest,
)
from qera_scaling.qubo import build_energy_spec

WEIGHTS = (1.0 / 3.0,) * 3


def _resolve_recorded_path(
    recorded: str, repository_root: Path, checkout_fallback: Path
) -> Path:
    """Resolve new relative manifests and relocate legacy absolute manifests."""

    candidate = Path(recorded)
    if not candidate.is_absolute():
        candidate = repository_root / candidate
    return candidate if candidate.is_file() else checkout_fallback


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, choices=(5, 6), required=True)
    parser.add_argument("--run-name", default=None)
    args = parser.parse_args()

    stage6a_root = Path(__file__).resolve().parents[1]
    instance = generate_instance(args.D)
    evaluator = ScalingEvaluator(instance)
    spec = build_energy_spec(evaluator, WEIGHTS, "cost")
    stem = f"{instance.instance_id}-p1"
    run_name = args.run_name or f"{stem}-uniform-cost"
    run_dir = stage6a_root / "artifacts" / "scaling" / "qaoa" / run_name
    manifest_path = run_dir / "manifest.json"
    raw_path = run_dir / "samples_raw.csv"
    if not manifest_path.is_file() or not raw_path.is_file():
        raise FileNotFoundError("execute the selected scaling QAOA run before processing")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") not in {"RAW_SAMPLE_SAVED", "PROCESSED"}:
        raise ValueError("run manifest does not contain a successful raw sample")
    if manifest["instance_id"] != instance.instance_id:
        raise ValueError("run manifest instance mismatch")
    if manifest["samples_raw_sha256"] != sha256_file(raw_path):
        raise ValueError("raw sample hash does not match the run manifest")
    # Older evidence manifests contain creator-machine absolute paths; relocate
    # those paths to the equivalent immutable pair in the current checkout.
    circuit_dir = stage6a_root / "artifacts" / "scaling" / "circuits"
    qprog_path = _resolve_recorded_path(
        manifest["qprog_path"],
        stage6a_root.parent,
        circuit_dir / f"{stem}.qprog",
    )
    synthesis_manifest_path = _resolve_recorded_path(
        manifest["synthesis_manifest_path"],
        stage6a_root.parent,
        circuit_dir / f"{stem}.synthesis.json",
    )
    validate_scaling_circuit_manifest(
        qprog_path,
        synthesis_manifest_path,
        spec,
        instance.instance_id,
        WEIGHTS,
    )

    declared_shots = int(manifest["final_shots"])
    frames = {
        "qaoa": pd.read_csv(raw_path),
        "uniform_random_bitstrings": random_bitstring_frame(
            instance.variable_count, declared_shots, instance.seed
        ),
        "uniform_random_valid_routes": random_valid_route_frame(
            evaluator, declared_shots, instance.seed
        ),
    }
    summaries = {}
    for method, frame in frames.items():
        processed, summary = process_sample_frame(
            frame,
            evaluator,
            spec,
            WEIGHTS,
            declared_shots=declared_shots,
        )
        if method == "qaoa":
            output_dir = run_dir
        else:
            output_dir = run_dir / "controls" / method
            output_dir.mkdir(parents=True, exist_ok=True)
            frame.to_csv(
                output_dir / "samples_raw.csv", index=False, lineterminator="\n"
            )
        processed.to_csv(
            output_dir / "samples.csv", index=False, lineterminator="\n"
        )
        (output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        summaries[method] = summary

    updated_manifest = {
        **manifest,
        "status": "PROCESSED",
        "samples_sha256": sha256_file(run_dir / "samples.csv"),
        "summary_sha256": sha256_file(run_dir / "summary.json"),
        "matched_control_seed": instance.seed,
        "matched_controls": [
            "uniform_random_bitstrings",
            "uniform_random_valid_routes",
        ],
    }
    manifest_path.write_text(
        json.dumps(updated_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(run_dir.resolve())
    print(json.dumps(summaries, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
