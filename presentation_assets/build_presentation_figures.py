"""Audit frozen Holy QOW evidence and render the six presentation figures.

This script is deliberately offline: it reads only committed CSV/JSON/raw artifacts.
It does not import Classiq or execute, synthesize, or optimize a quantum program.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "holy_qow_mplconfig"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation_assets"
TOL = 1e-12

NAVY = "#102A43"
BLUE = "#2F6BFF"
TEAL = "#00A896"
ORANGE = "#F4A261"
RED = "#D64550"
GRAY = "#8795A1"
LIGHT = "#E8EEF4"
INK = "#1F2933"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


checks: list[dict[str, Any]] = []
discrepancies: list[dict[str, Any]] = []


def plain(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def record_check(
    check_id: str,
    actual: Any,
    expected: Any,
    source: str,
    *,
    numeric: bool = False,
) -> None:
    if numeric:
        passed = bool(np.isclose(float(actual), float(expected), rtol=1e-10, atol=TOL))
    else:
        passed = actual == expected
    row = {
        "check_id": check_id,
        "status": "PASS" if passed else "FAIL",
        "actual": plain(actual),
        "expected": plain(expected),
        "source_artifact": source,
    }
    checks.append(row)
    if not passed:
        discrepancies.append(row)


def record_hash(check_id: str, relative: str, expected: str) -> None:
    path = ROOT / relative
    record_check(check_id, sha256(path), expected, relative)


def to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False})


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 17,
            "axes.titlesize": 23,
            "axes.labelsize": 18,
            "xtick.labelsize": 16,
            "ytick.labelsize": 16,
            "legend.fontsize": 15,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#B8C4CE",
            "axes.linewidth": 1.0,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": "#DDE5EC",
            "grid.linewidth": 1.0,
            "grid.alpha": 0.8,
        }
    )


def finish(fig: plt.Figure, filename: str) -> None:
    fig.savefig(OUT / filename, dpi=150, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 1. Held-out evidence: hash check, raw regrouping, and summary comparison.
# ---------------------------------------------------------------------------

heldout_results_rel = "artifacts/post6a/heldout/heldout_route_results.csv"
heldout_summary_rel = "artifacts/post6a/heldout/heldout_route_summary.csv"
heldout_eval_rel = "artifacts/post6a/heldout/evaluation_manifest.json"
heldout_route_manifest_rel = "artifacts/post6a/heldout/heldout_route_manifest.json"
heldout_scenario_manifest_rel = "artifacts/post6a/heldout/heldout_scenario_manifest.json"

heldout_eval = load_json(heldout_eval_rel)
record_hash(
    "heldout-results-hash",
    heldout_results_rel,
    heldout_eval["outputs"]["heldout_route_results_sha256"],
)
record_hash(
    "heldout-summary-hash",
    heldout_summary_rel,
    heldout_eval["outputs"]["heldout_route_summary_sha256"],
)
record_hash(
    "heldout-route-manifest-hash",
    heldout_route_manifest_rel,
    heldout_eval["route_manifest_sha256"],
)
record_hash(
    "heldout-scenario-manifest-hash",
    heldout_scenario_manifest_rel,
    heldout_eval["scenario_manifest_sha256"],
)

heldout_results = pd.read_csv(ROOT / heldout_results_rel)
heldout_summary = pd.read_csv(ROOT / heldout_summary_rel).set_index("route_id")
heldout_results["feasible"] = to_bool(heldout_results["feasible"])
record_check(
    "heldout-scenario-count",
    int(heldout_results["scenario_id"].nunique()),
    24,
    heldout_scenario_manifest_rel,
)

heldout_ids = ["nominal_only", "static_uniform_multiscenario", "exact_adaptive"]
for route_id in heldout_ids:
    raw = heldout_results.loc[heldout_results["route_id"] == route_id]
    summary = heldout_summary.loc[route_id]
    recomputed = {
        "scenario_count": int(len(raw)),
        "survival_rate": float(raw["feasible"].mean()),
        "violating_scenarios": int((~raw["feasible"]).sum()),
        "worst_case_regret": float(raw["regret"].max()),
        "maximum_overflow": float(raw["overflow"].max()),
    }
    for field, actual in recomputed.items():
        record_check(
            f"heldout-{route_id}-{field}",
            actual,
            summary[field],
            heldout_results_rel,
            numeric=field not in {"scenario_count", "violating_scenarios"},
        )

expected_heldout = {
    "nominal_only": (20 / 24, 4),
    "static_uniform_multiscenario": (1.0, 0),
    "exact_adaptive": (22 / 24, 2),
}
for route_id, (survival, violations) in expected_heldout.items():
    record_check(
        f"handoff-{route_id}-survival",
        heldout_summary.loc[route_id, "survival_rate"],
        survival,
        heldout_summary_rel,
        numeric=True,
    )
    record_check(
        f"handoff-{route_id}-violations",
        int(heldout_summary.loc[route_id, "violating_scenarios"]),
        violations,
        heldout_summary_rel,
    )


# ---------------------------------------------------------------------------
# 2. Quantum scaling: verify manifest-bound synthesis files and metrics.
# ---------------------------------------------------------------------------

scaling_manifest_rel = "stage6a/artifacts/scaling/tables/scaling_manifest.csv"
scaling_manifest = pd.read_csv(ROOT / scaling_manifest_rel).set_index("D")
scaling_expected = {
    4: (12, 65, 84, "COMPLETE"),
    5: (15, 79, 136, "COMPLETE"),
    6: (18, 138, 160, "COMPLETE"),
    8: (24, 246, 280, "SYNTHESIS_ONLY"),
}
scaling_rows: list[dict[str, Any]] = []
for demand_count, (width, depth, twoq, status) in scaling_expected.items():
    row = scaling_manifest.loc[demand_count]
    synthesis_rel = str(row["synthesis_manifest_path"]).replace("\\", "/")
    qprog_rel = str(row["qprog_path"]).replace("\\", "/")
    record_hash(
        f"scaling-D{demand_count}-synthesis-hash",
        synthesis_rel,
        str(row["synthesis_manifest_sha256"]),
    )
    record_hash(
        f"scaling-D{demand_count}-qprog-hash",
        qprog_rel,
        str(row["qprog_sha256"]),
    )
    synthesis = load_json(synthesis_rel)
    metrics = synthesis.get("metrics", synthesis)
    actual_width = int(metrics.get("width", metrics.get("synthesized_qubits")))
    actual_depth = int(metrics["depth"])
    actual_twoq = int(metrics.get("two_qubit_gate_count", metrics["count_ops"].get("cx", 0)))
    record_check(f"scaling-D{demand_count}-width", actual_width, width, synthesis_rel)
    record_check(f"scaling-D{demand_count}-depth", actual_depth, depth, synthesis_rel)
    record_check(f"scaling-D{demand_count}-twoq", actual_twoq, twoq, synthesis_rel)
    record_check(
        f"scaling-D{demand_count}-status",
        str(row["record_status"]),
        status,
        scaling_manifest_rel,
    )
    if demand_count == 8:
        record_check(
            "scaling-D8-no-qaoa-summary",
            bool(pd.isna(row["qaoa_summary_path"])),
            True,
            scaling_manifest_rel,
        )
    scaling_rows.append(
        {"D": demand_count, "qubits": actual_width, "depth": actual_depth, "twoq": actual_twoq}
    )
scaling = pd.DataFrame(scaling_rows).sort_values("D")


# ---------------------------------------------------------------------------
# 3. D=6 paired evidence: verify output hashes and recompute from sample rows.
# ---------------------------------------------------------------------------

repeat_rel = "artifacts/post6a/repeatability/d6_repeatability.csv"
control_rel = "artifacts/post6a/repeatability/d6_control_comparison.csv"
control_summary_rel = "artifacts/post6a/repeatability/d6_control_comparison_summary.json"
seed_summary_rel = "artifacts/post6a/repeatability/d6_seed_level_summary.csv"
repeat_manifest_rel = "artifacts/post6a/repeatability/manifest.json"
repeat_manifest = load_json(repeat_manifest_rel)
record_hash("repeatability-table-hash", repeat_rel, repeat_manifest["outputs"]["repeatability"])
record_hash("repeatability-control-hash", control_rel, repeat_manifest["outputs"]["control_comparison"])
record_hash(
    "repeatability-control-summary-hash",
    control_summary_rel,
    repeat_manifest["outputs"]["control_comparison_summary"],
)
record_hash("repeatability-seed-summary-hash", seed_summary_rel, repeat_manifest["outputs"]["seed_level_summary"])

for item in repeat_manifest["inputs"]:
    raw_path = Path(item["raw_path"])
    record_check(
        f"qaoa-seed-{item['optimizer_seed']}-raw-hash",
        sha256(raw_path),
        item["raw_sha256"],
        str(raw_path),
    )

repeat = pd.read_csv(ROOT / repeat_rel)
control_table = pd.read_csv(ROOT / control_rel).set_index("optimizer_seed")
control_summary = load_json(control_summary_rel)
seed_order = [6106, 6201, 6202, 6203, 6204]
record_check(
    "repeatability-seed-order",
    repeat_manifest["optimizer_seeds"],
    seed_order,
    repeat_manifest_rel,
)

paired: list[dict[str, Any]] = []
for seed in seed_order:
    seed_values: dict[str, Any] = {"seed": seed}
    for method in ("qaoa", "uniform_random_bitstrings"):
        row = repeat.loc[(repeat["optimizer_seed"] == seed) & (repeat["method"] == method)].iloc[0]
        if method == "qaoa":
            sample_rel = f"artifacts/post6a/repeatability/processed/seed-{seed}/samples.csv"
            summary_rel = f"artifacts/post6a/repeatability/processed/seed-{seed}/summary.json"
            prefix = "qaoa"
        else:
            sample_rel = f"artifacts/post6a/repeatability/controls/seed-{seed}/uniform_random_bitstrings/samples.csv"
            summary_rel = f"artifacts/post6a/repeatability/controls/seed-{seed}/uniform_random_bitstrings/summary.json"
            prefix = "random"
        samples = pd.read_csv(ROOT / sample_rel)
        samples["one_hot"] = to_bool(samples["one_hot"])
        samples["joint_feasible"] = to_bool(samples["joint_feasible"])
        summary = load_json(summary_rel)
        total = int(samples["counts"].sum())
        onehot_count = int(samples.loc[samples["one_hot"], "counts"].sum())
        feasible_count = int(samples.loc[samples["joint_feasible"], "counts"].sum())
        feasible_rows = samples.loc[samples["joint_feasible"]]
        best_objective = float(feasible_rows["weighted_cost"].min())
        best_gap = best_objective - float(summary["exact_joint_objective"])
        best_regret = float(feasible_rows["worst_case_regret"].min())
        record_check(f"D6-{seed}-{prefix}-shots", total, int(row["total_shots"]), sample_rel)
        record_check(f"D6-{seed}-{prefix}-onehot-count", onehot_count, int(row["one_hot_count"]), sample_rel)
        record_check(f"D6-{seed}-{prefix}-feasible-count", feasible_count, int(row["joint_feasible_count"]), sample_rel)
        record_check(
            f"D6-{seed}-{prefix}-gap-from-samples",
            best_gap,
            float(row["best_feasible_objective_gap"]),
            sample_rel,
            numeric=True,
        )
        record_check(
            f"D6-{seed}-{prefix}-regret-from-samples",
            best_regret,
            float(row["best_feasible_worst_case_regret"]),
            sample_rel,
            numeric=True,
        )
        record_check(
            f"D6-{seed}-{prefix}-gap-summary",
            float(summary["selected_exact_gap"]),
            float(row["best_feasible_objective_gap"]),
            summary_rel,
            numeric=True,
        )
        record_check(
            f"D6-{seed}-{prefix}-regret-summary",
            float(summary["best_sampled_worst_case_regret"]),
            float(row["best_feasible_worst_case_regret"]),
            summary_rel,
            numeric=True,
        )
        seed_values[f"{prefix}_gap"] = float(row["best_feasible_objective_gap"])
        seed_values[f"{prefix}_regret"] = float(row["best_feasible_worst_case_regret"])
    record_check(
        f"D6-{seed}-objective-direction",
        seed_values["qaoa_gap"] < seed_values["random_gap"],
        True,
        control_rel,
    )
    record_check(
        f"D6-{seed}-regret-direction",
        seed_values["qaoa_regret"] < seed_values["random_regret"],
        True,
        control_rel,
    )
    control_row = control_table.loc[seed]
    record_check(
        f"D6-{seed}-gap-delta",
        seed_values["qaoa_gap"] - seed_values["random_gap"],
        float(control_row["qaoa_minus_random_bit_best_objective_gap"]),
        control_rel,
        numeric=True,
    )
    record_check(
        f"D6-{seed}-regret-delta",
        seed_values["qaoa_regret"] - seed_values["random_regret"],
        float(control_row["qaoa_minus_random_bit_best_worst_case_regret"]),
        control_rel,
        numeric=True,
    )
    paired.append(seed_values)

paired_df = pd.DataFrame(paired)
record_check(
    "D6-five-of-five-objective-wins",
    int((paired_df["qaoa_gap"] < paired_df["random_gap"]).sum()),
    int(control_summary["best_objective_gap_pairwise_wins_over_random_bits"]),
    control_summary_rel,
)
record_check(
    "D6-five-of-five-regret-wins",
    int((paired_df["qaoa_regret"] < paired_df["random_regret"]).sum()),
    int(control_summary["best_worst_case_regret_pairwise_wins_over_random_bits"]),
    control_summary_rel,
)


# ---------------------------------------------------------------------------
# 4. Evolution and constrained-mixer backup evidence.
# ---------------------------------------------------------------------------

evolution_diag_rel = "artifacts/evolution_ablation/tables/evolution_diagnostics.json"
evolution_factor_rel = "artifacts/evolution_ablation/tables/evolution_factor_summary.csv"
evolution_policy_rel = "artifacts/evolution_ablation/tables/evolution_policy_comparison.csv"
evolution_diag = load_json(evolution_diag_rel)
record_hash("evolution-factor-hash", evolution_factor_rel, evolution_diag["output_hashes"]["factor_summary"])
record_hash("evolution-policy-hash", evolution_policy_rel, evolution_diag["output_hashes"]["policy_comparison"])
evolution_factor = pd.read_csv(ROOT / evolution_factor_rel)
evolution_policy = pd.read_csv(ROOT / evolution_policy_rel).set_index("policy_label")

static_survival = float(evolution_policy.loc["original_static_S3", "final_survival_rate"])
adaptive_survival = float(evolution_policy.loc["original_adaptive_S3", "final_survival_rate"])
s_rows = evolution_factor.loc[
    (evolution_factor["analysis_set"] == "B4-focused-rho0")
    & (evolution_factor["factor"] == "S")
    & (evolution_factor["value"].isin([5.0, 8.0, 12.0]))
]
s_ge_5_survival = float(s_rows["mean_final_survival"].mean())
rho_05_survival = float(
    evolution_factor.loc[
        (evolution_factor["analysis_set"] == "matched-B5-settings")
        & (evolution_factor["factor"] == "rho")
        & np.isclose(evolution_factor["value"], 0.5),
        "mean_final_survival",
    ].iloc[0]
)
record_check("evolution-original-static-survival", static_survival, 1.0, evolution_policy_rel, numeric=True)
record_check("evolution-original-adaptive-survival", adaptive_survival, 22 / 24, evolution_policy_rel, numeric=True)
record_check("evolution-S-ge-5-survival", s_ge_5_survival, 1.0, evolution_factor_rel, numeric=True)
record_check("evolution-rho-0.5-survival", rho_05_survival, 1.0, evolution_factor_rel, numeric=True)
record_check(
    "evolution-adaptive-does-not-beat-static",
    bool(evolution_diag["genuine_adaptive_beats_selected_static_on_final"]),
    False,
    evolution_diag_rel,
)

x_summary_rel = "artifacts/runs/uniform_cost_p1_smoke/summary.json"
x_raw_rel = "artifacts/runs/uniform_cost_p1_smoke/samples_raw.csv"
xy_gates_rel = "artifacts/stage6b/d4/d4_correctness_gates.json"
resource_rel = "artifacts/stage6b/tables/circuit_resource_comparison.csv"
resource_analysis_rel = "artifacts/stage6b/tables/circuit_resource_analysis.json"
x_summary = load_json(x_summary_rel)
x_raw = pd.read_csv(ROOT / x_raw_rel)
x_raw["one_hot_computed"] = x_raw["routes"].map(
    lambda value: all(sum(bits) == 1 for bits in np.asarray(ast.literal_eval(value)).reshape(-1, 3))
)
x_onehot = float(x_raw.loc[x_raw["one_hot_computed"], "counts"].sum() / x_raw["counts"].sum())
record_check("x-mixer-onehot-from-raw", x_onehot, x_summary["one_hot_probability"], x_raw_rel, numeric=True)
record_check("x-mixer-onehot-handoff", x_onehot, 0.05224609375, x_summary_rel, numeric=True)

xy_gates = load_json(xy_gates_rel)
xy_onehot = 1.0 - float(xy_gates["unoptimized_full_ansatz"]["sample_invalid_shots"]) / float(
    xy_gates["unoptimized_full_ansatz"]["sample_shots"]
)
record_check("xy-mixer-onehot", xy_onehot, 1.0, xy_gates_rel, numeric=True)
resources = pd.read_csv(ROOT / resource_rel).set_index("mixer")
resource_analysis = load_json(resource_analysis_rel)
record_hash("constraint-resource-table-hash", resource_rel, resource_analysis["table_sha256"])
for mixer, expected_depth, expected_twoq in (
    ("transverse_x_frozen", 65, 84),
    ("constraint_preserving_xy", 101, 164),
):
    record_check(f"{mixer}-depth", int(resources.loc[mixer, "depth"]), expected_depth, resource_rel)
    record_check(
        f"{mixer}-twoq", int(resources.loc[mixer, "two_qubit_gate_count"]), expected_twoq, resource_rel
    )


# ---------------------------------------------------------------------------
# 5. Exact-verification card evidence.
# ---------------------------------------------------------------------------

encoding_rel = "artifacts/tables/encoding_proof.json"
stage6b_verify_rel = "artifacts/stage6b/regression/final_verification.json"
evolution_verify_rel = "artifacts/evolution_ablation/final_verification.json"
encoding = load_json(encoding_rel)
stage6b_verify = load_json(stage6b_verify_rel)
evolution_verify = load_json(evolution_verify_rel)
record_check("exact-valid-assignments", int(encoding["valid_assignments_checked_per_run"]), 81, encoding_rel)
record_check("qubo-ising-bitstates", int(encoding["states_checked_per_run"]), 4096, encoding_rel)
integrated_tests = int(stage6b_verify["total_tests"]) + int(
    evolution_verify["tests"]["evolution_ablation"]["passed"]
)
integrated_failures = int(stage6b_verify["total_failures"]) + (0 if evolution_verify["status"] == "PASS" else 1)
record_check("integrated-test-count", integrated_tests, 132, f"{stage6b_verify_rel}; {evolution_verify_rel}")
record_check("integrated-test-failures", integrated_failures, 0, f"{stage6b_verify_rel}; {evolution_verify_rel}")


# Write the audit before plotting. A discrepancy blocks all presentation numbers.
audit = {
    "schema_version": "holy-qow-presentation-audit-v1",
    "offline_only": True,
    "classiq_jobs_run": 0,
    "check_count": len(checks),
    "passed": sum(row["status"] == "PASS" for row in checks),
    "failed": len(discrepancies),
    "status": "PASS" if not discrepancies else "FAIL",
    "checks": checks,
    "discrepancies": discrepancies,
}
(OUT / "SOURCE_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

log_lines = [
    "# Presentation Evidence Discrepancy Log",
    "",
    "This audit reads only frozen saved artifacts. It performs no quantum execution, synthesis, optimization, or new experiment.",
    "",
    f"- Checks: **{len(checks)}**",
    f"- Passed: **{audit['passed']}**",
    f"- Failed: **{audit['failed']}**",
    "",
]
if discrepancies:
    log_lines.extend(["## Discrepancies", ""])
    for item in discrepancies:
        log_lines.append(
            f"- `{item['check_id']}`: expected `{item['expected']}`, got `{item['actual']}` from `{item['source_artifact']}`."
        )
    log_lines.extend(["", "Affected numbers were omitted and figures were not generated."])
else:
    log_lines.extend(
        [
            "## Result",
            "",
            "No discrepancies were found. Every requested plotted number reproduced from the saved CSV/JSON/raw evidence within the declared numerical tolerance.",
            "",
            "The machine-readable check-by-check record is `SOURCE_AUDIT.json`.",
        ]
    )
(OUT / "DISCREPANCY_LOG.md").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

if discrepancies:
    raise SystemExit(f"Evidence audit failed with {len(discrepancies)} discrepancies; plots omitted.")


# ---------------------------------------------------------------------------
# 6. Six 16:9 projector-ready figures.
# ---------------------------------------------------------------------------

configure_plotting()

# MAIN-1: held-out robustness.
fig, ax = plt.subplots(figsize=(16, 9))
fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.16)
labels = ["Nominal\nrepresentative", "Static multi-environment", "Adaptive\nreweighting"]
route_ids = ["nominal_only", "static_uniform_multiscenario", "exact_adaptive"]
values = [float(heldout_summary.loc[r, "survival_rate"]) * 100 for r in route_ids]
violations = [int(heldout_summary.loc[r, "violating_scenarios"]) for r in route_ids]
bars = ax.bar(labels, values, color=[GRAY, TEAL, ORANGE], width=0.62)
ax.set_ylim(0, 112)
ax.set_ylabel("Held-out scenarios survived (%)")
ax.set_title("Static multi-environment routing survived all 24 unseen stresses", color=NAVY, weight="bold", pad=24)
ax.grid(axis="x", visible=False)
for bar, value, violation in zip(bars, values, violations):
    ax.text(bar.get_x() + bar.get_width() / 2, value + 2.2, f"{value:.1f}%", ha="center", weight="bold", fontsize=24, color=INK)
    ax.text(bar.get_x() + bar.get_width() / 2, value - 8.0, f"{violation} violations", ha="center", va="center", fontsize=18, color="white", weight="bold")
ax.text(
    0.01,
    -0.13,
    "Frozen held-out set: 24 demand, capacity, latency, and combined stresses. Nominal is one representative of a tied optimum.",
    transform=ax.transAxes,
    fontsize=14,
    color="#52616B",
)
finish(fig, "01_heldout_survival.png")

# MAIN-2: quantum resource scaling.
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9))
fig.subplots_adjust(left=0.07, right=0.98, top=0.81, bottom=0.16, wspace=0.18)
fig.suptitle("QAOA synthesis scaled to 24 route qubits", color=NAVY, weight="bold", fontsize=28, y=0.95)
d = scaling["D"].to_numpy()
ax1.plot(d, scaling["qubits"], color=BLUE, marker="o", markersize=12, linewidth=4)
for x, y in zip(d, scaling["qubits"]):
    ax1.text(x, y + 0.8, str(int(y)), ha="center", fontsize=18, weight="bold")
ax1.set_title("Route-register width")
ax1.set_xlabel("Demands D")
ax1.set_ylabel("Synthesized qubits")
ax1.set_xticks(d)
ax1.set_ylim(0, 29)

ax2.plot(d, scaling["depth"], color=ORANGE, marker="o", markersize=11, linewidth=4, label="Depth")
ax2.plot(d, scaling["twoq"], color=TEAL, marker="s", markersize=10, linewidth=4, label="2Q gates")
for x, depth, twoq in zip(d, scaling["depth"], scaling["twoq"]):
    ax2.annotate(str(int(depth)), (x, depth), xytext=(0, -27), textcoords="offset points", ha="center", color="#A85D00", fontsize=16, weight="bold")
    ax2.annotate(str(int(twoq)), (x, twoq), xytext=(0, 12), textcoords="offset points", ha="center", color="#006F63", fontsize=16, weight="bold")
ax2.axvspan(7.65, 8.35, color=LIGHT, zorder=-2)
ax2.text(8, 330, "D=8  synthesis only", ha="center", va="top", fontsize=15, color=NAVY, weight="bold")
ax2.set_title("Circuit cost")
ax2.set_xlabel("Demands D")
ax2.set_ylabel("Count")
ax2.set_xticks(d)
ax2.set_ylim(0, 340)
ax2.legend(loc="upper left", frameon=False)
fig.text(0.5, 0.045, "Fixed K=3 and p=1. Width is linear; depth and entangling-gate cost grow faster.", ha="center", fontsize=15, color="#52616B")
finish(fig, "02_quantum_scaling.png")

# MAIN-3: paired D=6 QAOA versus random bits.
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9))
fig.subplots_adjust(left=0.07, right=0.98, top=0.81, bottom=0.17, wspace=0.18)
fig.suptitle("D=6: QAOA found the better feasible route in all five paired runs", color=NAVY, weight="bold", fontsize=27, y=0.95)
x = np.arange(len(seed_order))
w = 0.36
for ax, qcol, rcol, title, ylabel in (
    (ax1, "qaoa_gap", "random_gap", "Best feasible objective gap", "Gap to exact optimum"),
    (ax2, "qaoa_regret", "random_regret", "Best feasible worst-case regret", "Worst-case regret"),
):
    qbars = ax.bar(x - w / 2, paired_df[qcol], width=w, color=TEAL, label="QAOA")
    rbars = ax.bar(x + w / 2, paired_df[rcol], width=w, color=GRAY, label="Random bits")
    ax.set_xticks(x, [str(s) for s in seed_order])
    ax.set_xlabel("Optimizer seed")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper left")
    ax.text(0.98, 0.93, "QAOA wins 5/5", transform=ax.transAxes, ha="right", va="top", fontsize=17, color=TEAL, weight="bold")
fig.text(
    0.5,
    0.045,
    "Lower is better. QAOA beat uninformed random-bit sampling 5/5, but did not beat sampling restricted to valid routes. No quantum-advantage claim.",
    ha="center",
    fontsize=15,
    color="#52616B",
)
finish(fig, "03_d6_qaoa_vs_random_bits.png")

# BACKUP-1: evolution ablation.
fig, ax = plt.subplots(figsize=(16, 9))
fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.17)
evolution_labels = ["Static\nS=3", "Adaptive S=3\nη=1", "Focused grid\nS≥5", "Diversity floor\nρ=0.5"]
evolution_values = np.array([static_survival, adaptive_survival, s_ge_5_survival, rho_05_survival]) * 100
evolution_colors = [TEAL, RED, BLUE, ORANGE]
bars = ax.bar(evolution_labels, evolution_values, color=evolution_colors, width=0.64)
ax.set_ylim(0, 112)
ax.set_ylabel("Final held-out survival (%)")
ax.set_title("Too much pressure on too few environments caused over-specialization", color=NAVY, weight="bold", pad=24)
ax.grid(axis="x", visible=False)
for bar, value in zip(bars, evolution_values):
    ax.text(bar.get_x() + bar.get_width() / 2, value + 2.1, f"{value:.1f}%", ha="center", fontsize=23, weight="bold")
ax.text(
    0.5,
    -0.14,
    "More training environments or a diversity floor prevented the harmful route switch. Adaptation did not beat static weighting.",
    transform=ax.transAxes,
    ha="center",
    fontsize=16,
    color="#52616B",
)
finish(fig, "backup_01_evolution_ablation.png")

# BACKUP-2: constraint-preserving mixer tradeoff.
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9))
fig.subplots_adjust(left=0.07, right=0.98, top=0.81, bottom=0.17, wspace=0.18)
fig.suptitle("Constraint preservation fixes validity and increases circuit cost", color=NAVY, weight="bold", fontsize=27, y=0.95)
mixer_labels = ["X mixer", "Constrained mixer"]
onehot_values = [x_onehot * 100, xy_onehot * 100]
bars = ax1.bar(mixer_labels, onehot_values, color=[GRAY, TEAL], width=0.62)
ax1.set_title("One-hot sample probability")
ax1.set_ylabel("One-hot samples (%)")
ax1.set_ylim(0, 115)
ax1.grid(axis="x", visible=False)
for bar, value in zip(bars, onehot_values):
    ax1.text(bar.get_x() + bar.get_width() / 2, value + 2.5, f"{value:.3g}%", ha="center", fontsize=23, weight="bold")

metric_x = np.arange(2)
depths = [int(resources.loc["transverse_x_frozen", "depth"]), int(resources.loc["constraint_preserving_xy", "depth"])]
twoqs = [int(resources.loc["transverse_x_frozen", "two_qubit_gate_count"]), int(resources.loc["constraint_preserving_xy", "two_qubit_gate_count"])]
ax2.bar(metric_x - w / 2, depths, width=w, color=ORANGE, label="Depth")
ax2.bar(metric_x + w / 2, twoqs, width=w, color=BLUE, label="2Q gates")
ax2.set_xticks(metric_x, mixer_labels)
ax2.set_title("D=4 p=1 resource cost")
ax2.set_ylabel("Count")
ax2.set_ylim(0, 190)
ax2.grid(axis="x", visible=False)
ax2.legend(frameon=False, loc="upper left")
for i, (depth, twoq) in enumerate(zip(depths, twoqs)):
    ax2.text(i - w / 2, depth + 4, str(depth), ha="center", fontsize=18, weight="bold")
    ax2.text(i + w / 2, twoq + 4, str(twoq), ha="center", fontsize=18, weight="bold")
fig.text(0.5, 0.045, "Structural leakage solved. No reproducible p=1 route-quality advantage over uniform-valid sampling.", ha="center", fontsize=15, color="#52616B")
finish(fig, "backup_02_constraint_mixer.png")

# BACKUP-3: exact verification / auditability.
fig = plt.figure(figsize=(16, 9), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_axis_off()
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.text(0.06, 0.88, "Exact checks anchor every small-instance quantum claim", fontsize=29, color=NAVY, weight="bold", transform=ax.transAxes)
items = [
    ("81", "valid D=4 routes", "exhaustively evaluated"),
    ("4,096", "binary states", "QUBO and Ising energies checked"),
    ("132 / 0", "tests passed / failed", "across the integrated evidence suites"),
]
xs = [0.18, 0.50, 0.82]
for index, ((number, label, detail), xpos) in enumerate(zip(items, xs)):
    ax.text(xpos, 0.58, number, ha="center", va="center", fontsize=48, color=TEAL if index != 2 else BLUE, weight="bold", transform=ax.transAxes)
    ax.text(xpos, 0.43, label, ha="center", fontsize=20, color=INK, weight="bold", transform=ax.transAxes)
    ax.text(xpos, 0.35, detail, ha="center", fontsize=15, color="#52616B", transform=ax.transAxes)
for xpos in (0.34, 0.66):
    ax.plot([xpos, xpos], [0.30, 0.70], color=LIGHT, linewidth=3, transform=ax.transAxes)
ax.text(0.5, 0.13, "Saved raw samples, manifests, hashes, and exact references make every result traceable.", ha="center", fontsize=18, color=NAVY, transform=ax.transAxes)
finish(fig, "backup_03_verification.png")


# ---------------------------------------------------------------------------
# 7. Slide-number evidence table for the six figures produced in this pass.
# ---------------------------------------------------------------------------

number_columns = [
    "claim_id",
    "slide",
    "metric",
    "value",
    "unit",
    "source_artifact",
    "source_field_or_row",
    "notes",
]
number_rows: list[dict[str, Any]] = []


def add_number(
    claim_id: str,
    slide: str,
    metric: str,
    value: Any,
    unit: str,
    source_artifact: str,
    source_field_or_row: str,
    notes: str = "",
) -> None:
    number_rows.append(
        {
            "claim_id": claim_id,
            "slide": slide,
            "metric": metric,
            "value": value,
            "unit": unit,
            "source_artifact": source_artifact,
            "source_field_or_row": source_field_or_row,
            "notes": notes,
        }
    )


for route_id, label in (
    ("nominal_only", "nominal"),
    ("static_uniform_multiscenario", "static_multienvironment"),
    ("exact_adaptive", "adaptive"),
):
    row = heldout_summary.loc[route_id]
    survived = int(round(float(row["survival_rate"]) * int(row["scenario_count"])))
    add_number(
        f"MAIN1-{label}-survived",
        "MAIN-1",
        f"{label}_scenarios_survived",
        survived,
        "scenarios",
        heldout_summary_rel,
        f"route_id={route_id}; survival_rate * scenario_count",
    )
    add_number(
        f"MAIN1-{label}-scenario-count",
        "MAIN-1",
        f"{label}_scenario_count",
        int(row["scenario_count"]),
        "scenarios",
        heldout_summary_rel,
        f"route_id={route_id}; scenario_count",
    )
    add_number(
        f"MAIN1-{label}-survival",
        "MAIN-1",
        f"{label}_survival",
        float(row["survival_rate"]) * 100,
        "percent",
        heldout_summary_rel,
        f"route_id={route_id}; survival_rate",
        "Chart displays one decimal place.",
    )
    add_number(
        f"MAIN1-{label}-violations",
        "MAIN-1",
        f"{label}_capacity_violations",
        int(row["violating_scenarios"]),
        "scenarios",
        heldout_summary_rel,
        f"route_id={route_id}; violating_scenarios",
    )

for item in scaling.to_dict(orient="records"):
    demand_count = int(item["D"])
    synthesis_rel = str(scaling_manifest.loc[demand_count, "synthesis_manifest_path"]).replace("\\", "/")
    add_number(f"MAIN2-D{demand_count}-D", "MAIN-2", "demand_count", demand_count, "demands", scaling_manifest_rel, "D")
    add_number(
        f"MAIN2-D{demand_count}-qubits",
        "MAIN-2",
        "synthesized_qubits",
        int(item["qubits"]),
        "qubits",
        synthesis_rel,
        "metrics.width" if demand_count == 4 else "synthesized_qubits",
    )
    add_number(
        f"MAIN2-D{demand_count}-depth",
        "MAIN-2",
        "circuit_depth",
        int(item["depth"]),
        "layers",
        synthesis_rel,
        "metrics.depth" if demand_count == 4 else "depth",
    )
    add_number(
        f"MAIN2-D{demand_count}-twoq",
        "MAIN-2",
        "two_qubit_gates",
        int(item["twoq"]),
        "gates",
        synthesis_rel,
        "metrics.count_ops.cx" if demand_count == 4 else "two_qubit_gate_count",
        "D=8 is synthesis-only." if demand_count == 8 else "",
    )
add_number("MAIN2-K", "MAIN-2", "paths_per_demand", 3, "paths", repeat_manifest_rel, "frozen_configuration / circuit width D*K", "Fixed K.")
add_number("MAIN2-p", "MAIN-2", "qaoa_depth", 1, "layers", repeat_manifest_rel, "frozen_configuration.qaoa_depth")

for item in paired_df.to_dict(orient="records"):
    seed = int(item["seed"])
    q_summary_rel = f"artifacts/post6a/repeatability/processed/seed-{seed}/summary.json"
    r_summary_rel = f"artifacts/post6a/repeatability/controls/seed-{seed}/uniform_random_bitstrings/summary.json"
    add_number(f"MAIN3-seed-{seed}", "MAIN-3", "optimizer_seed", seed, "seed", repeat_rel, f"optimizer_seed={seed}")
    add_number(
        f"MAIN3-{seed}-qaoa-gap",
        "MAIN-3",
        "qaoa_best_feasible_objective_gap",
        item["qaoa_gap"],
        "normalized objective gap",
        q_summary_rel,
        "selected_exact_gap",
    )
    add_number(
        f"MAIN3-{seed}-random-gap",
        "MAIN-3",
        "random_bit_best_feasible_objective_gap",
        item["random_gap"],
        "normalized objective gap",
        r_summary_rel,
        "selected_exact_gap",
    )
    add_number(
        f"MAIN3-{seed}-qaoa-regret",
        "MAIN-3",
        "qaoa_best_feasible_worst_case_regret",
        item["qaoa_regret"],
        "normalized regret",
        q_summary_rel,
        "best_sampled_worst_case_regret",
    )
    add_number(
        f"MAIN3-{seed}-random-regret",
        "MAIN-3",
        "random_bit_best_feasible_worst_case_regret",
        item["random_regret"],
        "normalized regret",
        r_summary_rel,
        "best_sampled_worst_case_regret",
    )
add_number(
    "MAIN3-objective-wins",
    "MAIN-3",
    "qaoa_objective_pairwise_wins",
    int(control_summary["best_objective_gap_pairwise_wins_over_random_bits"]),
    "of 5 seeds",
    control_summary_rel,
    "best_objective_gap_pairwise_wins_over_random_bits",
)
add_number(
    "MAIN3-regret-wins",
    "MAIN-3",
    "qaoa_regret_pairwise_wins",
    int(control_summary["best_worst_case_regret_pairwise_wins_over_random_bits"]),
    "of 5 seeds",
    control_summary_rel,
    "best_worst_case_regret_pairwise_wins_over_random_bits",
)

for claim_id, metric, value, source, selector, notes in (
    ("BACKUP1-static", "original_static_S3_survival", static_survival * 100, evolution_policy_rel, "policy_label=original_static_S3; final_survival_rate", ""),
    ("BACKUP1-adaptive", "original_adaptive_S3_eta1_survival", adaptive_survival * 100, evolution_policy_rel, "policy_label=original_adaptive_S3; final_survival_rate", "S=3, eta=1, T=3, rho=0."),
    ("BACKUP1-Sge5", "focused_S_ge_5_mean_survival", s_ge_5_survival * 100, evolution_factor_rel, "analysis_set=B4-focused-rho0; factor=S; values=5,8,12; mean_final_survival", "Mean of the three frozen factor-summary rows; every row equals 100%."),
    ("BACKUP1-rho05", "rho_0_5_aggregate_survival", rho_05_survival * 100, evolution_factor_rel, "analysis_set=matched-B5-settings; factor=rho; value=0.5; mean_final_survival", ""),
):
    add_number(claim_id, "BACKUP-1", metric, value, "percent", source, selector, notes)
add_number("BACKUP1-S", "BACKUP-1", "original_training_environment_count", 3, "environments", evolution_policy_rel, "policy_label=original_adaptive_S3; S")
add_number("BACKUP1-eta", "BACKUP-1", "original_selection_strength", 1.0, "eta", evolution_policy_rel, "policy_label=original_adaptive_S3; eta")
add_number("BACKUP1-S-threshold", "BACKUP-1", "focused_environment_threshold", 5, "environments", evolution_factor_rel, "factor=S; values 5,8,12")
add_number("BACKUP1-rho", "BACKUP-1", "diversity_mixing", 0.5, "rho", evolution_factor_rel, "analysis_set=matched-B5-settings; factor=rho; value=0.5")

for claim_id, metric, value, source, selector, unit in (
    ("BACKUP2-x-onehot", "x_mixer_onehot_probability", x_onehot * 100, x_summary_rel, "one_hot_probability", "percent"),
    ("BACKUP2-xy-onehot", "constraint_mixer_onehot_probability", xy_onehot * 100, xy_gates_rel, "unoptimized_full_ansatz.sample_invalid_shots / sample_shots", "percent"),
    ("BACKUP2-x-depth", "x_mixer_depth", depths[0], resource_rel, "mixer=transverse_x_frozen; depth", "layers"),
    ("BACKUP2-xy-depth", "constraint_mixer_depth", depths[1], resource_rel, "mixer=constraint_preserving_xy; depth", "layers"),
    ("BACKUP2-x-twoq", "x_mixer_two_qubit_gates", twoqs[0], resource_rel, "mixer=transverse_x_frozen; two_qubit_gate_count", "gates"),
    ("BACKUP2-xy-twoq", "constraint_mixer_two_qubit_gates", twoqs[1], resource_rel, "mixer=constraint_preserving_xy; two_qubit_gate_count", "gates"),
):
    add_number(claim_id, "BACKUP-2", metric, value, unit, source, selector)
add_number("BACKUP2-D", "BACKUP-2", "demand_count", 4, "demands", resource_rel, "D")
add_number("BACKUP2-p", "BACKUP-2", "qaoa_depth", 1, "layers", resource_rel, "p")

add_number("BACKUP3-routes", "BACKUP-3", "exact_valid_routes", 81, "routes", encoding_rel, "valid_assignments_checked_per_run")
add_number("BACKUP3-bitstates", "BACKUP-3", "qubo_ising_states_checked", 4096, "bitstrings", encoding_rel, "states_checked_per_run")
add_number("BACKUP3-tests-passed", "BACKUP-3", "integrated_tests_passed", 132, "tests", f"{stage6b_verify_rel}; {evolution_verify_rel}", "stage6b total_tests + evolution_ablation passed")
add_number("BACKUP3-tests-failed", "BACKUP-3", "integrated_tests_failed", 0, "tests", f"{stage6b_verify_rel}; {evolution_verify_rel}", "stage6b total_failures + evolution status")

pd.DataFrame(number_rows, columns=number_columns).to_csv(OUT / "PRESENTATION_NUMBERS.csv", index=False)


figure_sources = {
    "01_heldout_survival.png": [heldout_results_rel, heldout_summary_rel, heldout_eval_rel],
    "02_quantum_scaling.png": [scaling_manifest_rel] + [
        str(scaling_manifest.loc[d, "synthesis_manifest_path"]).replace("\\", "/") for d in scaling_expected
    ],
    "03_d6_qaoa_vs_random_bits.png": [repeat_rel, control_rel, control_summary_rel, repeat_manifest_rel],
    "backup_01_evolution_ablation.png": [evolution_factor_rel, evolution_policy_rel, evolution_diag_rel],
    "backup_02_constraint_mixer.png": [x_summary_rel, x_raw_rel, xy_gates_rel, resource_rel, resource_analysis_rel],
    "backup_03_verification.png": [encoding_rel, stage6b_verify_rel, evolution_verify_rel],
}
figure_manifest = {
    "schema_version": "holy-qow-presentation-figures-v1",
    "audit_status": audit["status"],
    "figure_count": len(figure_sources),
    "presentation_number_count": len(number_rows),
    "presentation_numbers_sha256": sha256(OUT / "PRESENTATION_NUMBERS.csv"),
    "figures": {
        filename: {
            "sha256": sha256(OUT / filename),
            "pixel_dimensions": [2400, 1350],
            "sources": sources,
        }
        for filename, sources in figure_sources.items()
    },
}
(OUT / "FIGURE_MANIFEST.json").write_text(json.dumps(figure_manifest, indent=2) + "\n", encoding="utf-8")

print(json.dumps({"audit": audit["status"], "checks": len(checks), "figures": list(figure_sources)}, indent=2))
