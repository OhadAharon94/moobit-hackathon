"""Human-readable audit trail for the adaptive Holy Qow decision."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from qera.config import SCENARIO_ORDER


def build_decision_trace(
    summary: Mapping[str, Any], scenario_names: Sequence[str] = SCENARIO_ORDER
) -> list[dict[str, Any]]:
    """Convert a saved adaptive summary into presentation-ready trace rows."""

    steps = summary.get("steps", [])
    source_runs = summary.get("source_runs", [])
    rows: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        weights = tuple(float(value) for value in step["request"]["scenario_weights"])
        regrets = tuple(float(value) for value in step["regrets"])
        if len(weights) != len(scenario_names) or len(regrets) != len(scenario_names):
            raise ValueError("decision trace scenario dimensions do not match")
        maximum = max(regrets)
        stressed = [
            name
            for name, regret in zip(scenario_names, regrets, strict=True)
            if abs(regret - maximum) <= 1e-12
        ]
        if index + 1 < len(steps):
            next_weights = tuple(
                float(value)
                for value in steps[index + 1]["request"]["scenario_weights"]
            )
            stressed_changes = ", ".join(
                f"{name} {weights[position]:.3f}→{next_weights[position]:.3f}"
                for position, name in enumerate(scenario_names)
                if name in stressed
            )
            explanation = (
                f"Highest regret: {', '.join(stressed)} ({maximum:.3f}); "
                f"next weight: {stressed_changes}."
            )
        else:
            explanation = "Final solve; choose the lowest worst-regret route observed."
        metadata = step["result"].get("metadata", {})
        row: dict[str, Any] = {
            "iteration": index + 1,
            "source_run": source_runs[index] if index < len(source_runs) else "",
            "seed": step["request"]["seed"],
            **{
                f"weight_{name}": weights[position]
                for position, name in enumerate(scenario_names)
            },
            "selected_route": json.dumps(step["result"]["assignment"]),
            **{
                f"regret_{name}": regrets[position]
                for position, name in enumerate(scenario_names)
            },
            "worst_regret": maximum,
            "stressed_scenario": ", ".join(stressed),
            "joint_feasible_probability": metadata.get(
                "joint_feasible_probability"
            ),
            "best_so_far": json.dumps(step["best_so_far"]),
            "update_explanation": explanation,
        }
        rows.append(row)
    return rows


def write_decision_trace(
    summary_path: Path, csv_path: Path, markdown_path: Path
) -> None:
    """Write stable machine-readable and pitch-ready versions of the trace."""

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = build_decision_trace(summary)
    if not rows:
        raise ValueError("adaptive summary contains no completed steps")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Holy Qow adaptive decision trace",
        "",
        "Every saved step is recoverable from inputs, scenario weights, "
        "quantum samples, feasibility checks, and deterministic tie-breaking.",
        "",
        "| Step | Scenario weights (nominal / surge / degradation) | Selected route | Worst regret | Decision explanation |",
        "|---:|---|---|---:|---|",
    ]
    for row in rows:
        weights = " / ".join(
            f"{row[f'weight_{name}']:.3f}" for name in SCENARIO_ORDER
        )
        lines.append(
            f"| {row['iteration']} | {weights} | `{row['selected_route']}` | "
            f"{row['worst_regret']:.3f} | {row['update_explanation']} |"
        )
    initial = rows[0]["worst_regret"]
    best = min(row["worst_regret"] for row in rows)
    if initial > 0.0:
        comparison = (
            f"Across the three frozen training scenarios, the best observed "
            f"worst-case regret changed from **{initial:.3f}** at the first step "
            f"to **{best:.3f}** ({100.0 * (initial - best) / initial:.1f}% lower)."
        )
    else:
        comparison = (
            "Across the three frozen training scenarios, the initial and best "
            "observed worst-case regrets were both **0.000**."
        )
    lines += [
        "",
        comparison,
        "This is an in-training trace, not a held-out robustness result; the "
        "adaptive route did not beat static uniform multi-environment training "
        "on the frozen 24-scenario held-out set.",
        "",
    ]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
