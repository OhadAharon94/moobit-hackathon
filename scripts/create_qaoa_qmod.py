"""Create the Stage 3 uniform-cost p=1 Qmod artifact without synthesis."""

from __future__ import annotations

from pathlib import Path

from qera.config import INITIAL_SCENARIO_WEIGHTS
from qera.energy import build_energy_spec
from qera.evaluate import Evaluator
from qera.qaoa_model import create_qmod


def main() -> None:
    spec = build_energy_spec(
        Evaluator(), INITIAL_SCENARIO_WEIGHTS, "cost", energy_mode="base"
    )
    qmod = create_qmod(spec, depth=1)
    output = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / "circuits"
        / "uniform_cost_p1.qmod.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(qmod, encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()
