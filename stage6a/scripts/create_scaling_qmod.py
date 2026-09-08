"""Serialize Stage 6A QAOA models locally without platform access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qera_scaling.classiq_model import create_qmod
from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.instances import generate_instance
from qera_scaling.qubo import build_energy_spec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--D", type=int, choices=(4, 5, 6, 8), required=True)
    args = parser.parse_args()
    instance = generate_instance(args.D)
    spec = build_energy_spec(ScalingEvaluator(instance), (1.0 / 3.0,) * 3, "cost")
    output = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "scaling"
        / "circuits"
        / f"{instance.instance_id}-p1.qmod.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    model = create_qmod(spec, depth=1)
    output.write_text(
        json.dumps(json.loads(model), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output.resolve())


if __name__ == "__main__":
    main()
