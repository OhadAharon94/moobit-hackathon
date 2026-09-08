"""Post-process the frozen validation-first ablation without retuning on final data."""

from __future__ import annotations

import json
from math import isclose

import numpy as np
import pandas as pd

from holy_qow_evolution.common import artifact_root, sha256_file, write_csv, write_json


def selection_columns(frame: pd.DataFrame) -> list[str]:
    return [
        "validation_survival_rate",
        "validation_maximum_overflow",
        "validation_worst_regret",
        "validation_mean_regret",
        "validation_nominal_cost",
        "S",
        "eta",
        "T",
        "rho",
        "run_id",
    ]


def validation_sort(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        selection_columns(frame),
        ascending=[False, True, True, True, True, True, True, True, True, True],
        kind="stable",
    )


def correlation(x: pd.Series, y: pd.Series, method: str = "pearson") -> float | None:
    if len(x) < 3 or x.nunique() < 2 or y.nunique() < 2:
        return None
    value = x.corr(y, method=method)
    return None if pd.isna(value) else float(value)


def policy_row(label: str, selection_basis: str, row: pd.Series) -> dict:
    fields = [
        "run_id", "S", "eta", "T", "rho", "final_assignment",
        "final_effective_environments", "final_effective_fraction", "final_maximum_weight",
        "validation_survival_rate", "validation_mean_regret", "validation_worst_regret",
        "validation_violating_scenarios", "validation_maximum_overflow",
        "final_survival_rate", "final_mean_regret", "final_worst_regret",
        "final_violating_scenarios", "final_mean_overflow", "final_maximum_overflow",
        "final_mean_maximum_utilization", "final_worst_maximum_utilization",
        "final_mean_weighted_latency", "final_maximum_weighted_latency", "final_nominal_cost",
    ]
    return {"policy_label": label, "selection_basis": selection_basis, **{field: row[field] for field in fields}}


def main() -> None:
    out = artifact_root()
    tables = out / "tables"
    manifests = out / "manifests"
    validation_path = tables / "evolution_validation_results.csv"
    grid_path = tables / "evolution_grid_results.csv"
    selection_path = manifests / "selection_before_final.json"
    for path in (validation_path, grid_path, selection_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    # Correct the purely semantic T=1 eligibility ambiguity using validation columns only.
    validation = pd.read_csv(validation_path)
    genuine = validation[(validation["eta"] > 0.0) & (validation["T"] > 1)].copy()
    selected_genuine = validation_sort(genuine).iloc[0]
    eligibility = {
        "schema_version": "holy-qow-evolution-adaptive-eligibility-v1",
        "status": "VALIDATION_ONLY_SUPPLEMENT",
        "reason": "The predeclared eta>0 filter admitted T=1 edge cases, but T=1 applies no weight update. This supplement identifies the best policy with at least one adaptive update.",
        "eligibility": "eta > 0 and T > 1",
        "selection_rule": json.loads(selection_path.read_text(encoding="utf-8"))["selection_rule"],
        "validation_summary_sha256": sha256_file(validation_path),
        "selected_genuinely_adaptive_run_id": selected_genuine["run_id"],
        "selected_genuinely_adaptive_assignment": selected_genuine["final_assignment"],
        "final_test_columns_used": False,
        "posthoc_change_to_predeclared_grid": False,
    }
    eligibility_path = write_json(manifests / "adaptive_eligibility_supplement.json", eligibility)

    grid = pd.read_csv(grid_path)
    by_id = grid.set_index("run_id", drop=False)
    frozen_selection = json.loads(selection_path.read_text(encoding="utf-8"))
    original_adaptive_id = "B4-focused-s3-eta1-t3-rho0"
    policy_rows = [
        policy_row("original_static_S3", "frozen original static control", by_id.loc[frozen_selection["original_s3_static_run_id"]]),
        policy_row("original_adaptive_S3", "frozen original eta=1,T=3,rho=0", by_id.loc[original_adaptive_id]),
        policy_row("validation_selected_static", "predeclared validation-only selection", by_id.loc[frozen_selection["selected_static_uniform_run_id"]]),
        policy_row("nominal_adaptive_selection_T1", "predeclared eta>0 selection; zero updates at T=1", by_id.loc[frozen_selection["selected_adaptive_run_id"]]),
        policy_row("validation_selected_genuine_adaptive", "validation-only supplement requiring T>1", by_id.loc[selected_genuine["run_id"]]),
    ]
    policy_path = write_csv(tables / "evolution_policy_comparison.csv", policy_rows)

    route_rows = []
    for assignment, group in grid.groupby("final_assignment", sort=True):
        first = group.iloc[0]
        route_rows.append(
            {
                "assignment": assignment,
                "run_count": len(group),
                "validation_survival_rate": first["validation_survival_rate"],
                "validation_mean_regret": first["validation_mean_regret"],
                "validation_worst_regret": first["validation_worst_regret"],
                "final_survival_rate": first["final_survival_rate"],
                "final_mean_regret": first["final_mean_regret"],
                "final_worst_regret": first["final_worst_regret"],
                "final_violating_scenarios": first["final_violating_scenarios"],
                "final_maximum_overflow": first["final_maximum_overflow"],
            }
        )
    route_path = write_csv(tables / "evolution_route_catalog.csv", route_rows)

    factor_rows = []
    focused = grid[grid["run_family"] == "B4-focused"]
    for factor in ("S", "eta", "T"):
        for value, group in focused.groupby(factor, sort=True):
            factor_rows.append(
                {
                    "analysis_set": "B4-focused-rho0",
                    "factor": factor,
                    "value": value,
                    "run_count": len(group),
                    "distinct_routes": group["final_assignment"].nunique(),
                    "mean_validation_survival": group["validation_survival_rate"].mean(),
                    "mean_validation_worst_regret": group["validation_worst_regret"].mean(),
                    "mean_final_survival": group["final_survival_rate"].mean(),
                    "mean_final_worst_regret": group["final_worst_regret"].mean(),
                    "mean_effective_fraction": group["final_effective_fraction"].mean(),
                }
            )
    rho_frame = pd.concat(
        [
            focused[(focused["eta"] > 0.0)],
            grid[grid["run_family"] == "B5-diversity"],
        ],
        ignore_index=True,
    )
    for value, group in rho_frame.groupby("rho", sort=True):
        factor_rows.append(
            {
                "analysis_set": "matched-B5-settings",
                "factor": "rho",
                "value": value,
                "run_count": len(group),
                "distinct_routes": group["final_assignment"].nunique(),
                "mean_validation_survival": group["validation_survival_rate"].mean(),
                "mean_validation_worst_regret": group["validation_worst_regret"].mean(),
                "mean_final_survival": group["final_survival_rate"].mean(),
                "mean_final_worst_regret": group["final_worst_regret"].mean(),
                "mean_effective_fraction": group["final_effective_fraction"].mean(),
            }
        )
    factor_path = write_csv(tables / "evolution_factor_summary.csv", factor_rows)

    rho_rows = []
    for _, candidate in grid[grid["run_family"] == "B5-diversity"].iterrows():
        baseline = focused[
            (focused["S"] == candidate["S"])
            & np.isclose(focused["eta"], candidate["eta"])
            & (focused["T"] == candidate["T"])
            & np.isclose(focused["rho"], 0.0)
        ].iloc[0]
        rho_rows.append(
            {
                "S": candidate["S"], "eta": candidate["eta"], "T": candidate["T"], "rho": candidate["rho"],
                "baseline_run_id": baseline["run_id"], "mixed_run_id": candidate["run_id"],
                "baseline_assignment": baseline["final_assignment"], "mixed_assignment": candidate["final_assignment"],
                "route_changed": baseline["final_assignment"] != candidate["final_assignment"],
                "validation_survival_delta": candidate["validation_survival_rate"] - baseline["validation_survival_rate"],
                "validation_worst_regret_improvement": baseline["validation_worst_regret"] - candidate["validation_worst_regret"],
                "final_survival_delta": candidate["final_survival_rate"] - baseline["final_survival_rate"],
                "final_worst_regret_improvement": baseline["final_worst_regret"] - candidate["final_worst_regret"],
                "effective_fraction_increase": candidate["final_effective_fraction"] - baseline["final_effective_fraction"],
            }
        )
    rho_path = write_csv(tables / "evolution_rho_pairwise.csv", rho_rows)

    adaptive = grid[(grid["eta"] > 0.0) & (grid["T"] > 1)].copy()
    adaptive["collapse_fraction"] = 1.0 - adaptive["final_effective_fraction"]
    correlations = {
        "population": "all predeclared eta>0,T>1 runs",
        "run_count": len(adaptive),
        "raw_N_eff_warning": "N_eff scales with S; collapse_fraction=1-N_eff/S is the primary measure.",
        "collapse_vs_final_worst_regret": {
            "pearson": correlation(adaptive["collapse_fraction"], adaptive["final_worst_regret"]),
            "spearman": correlation(adaptive["collapse_fraction"], adaptive["final_worst_regret"], "spearman"),
        },
        "collapse_vs_final_mean_regret": {
            "pearson": correlation(adaptive["collapse_fraction"], adaptive["final_mean_regret"]),
            "spearman": correlation(adaptive["collapse_fraction"], adaptive["final_mean_regret"], "spearman"),
        },
        "collapse_vs_final_survival": {
            "pearson": correlation(adaptive["collapse_fraction"], adaptive["final_survival_rate"]),
            "spearman": correlation(adaptive["collapse_fraction"], adaptive["final_survival_rate"], "spearman"),
        },
        "within_S_collapse_vs_final_worst_regret": {
            str(s): {
                "run_count": len(group),
                "pearson": correlation(group["collapse_fraction"], group["final_worst_regret"]),
                "spearman": correlation(group["collapse_fraction"], group["final_worst_regret"], "spearman"),
            }
            for s, group in adaptive.groupby("S", sort=True)
        },
    }
    correlation_path = write_json(tables / "evolution_correlations.json", correlations)

    original_adaptive = by_id.loc[original_adaptive_id]
    original_static = by_id.loc[frozen_selection["original_s3_static_run_id"]]
    genuine_row = by_id.loc[selected_genuine["run_id"]]
    static_row = by_id.loc[frozen_selection["selected_static_uniform_run_id"]]
    rho_table = pd.DataFrame(rho_rows)
    diagnostics = {
        "schema_version": "holy-qow-evolution-diagnostics-v1",
        "configuration_count": len(grid),
        "all_exact_best_response_checks_pass": bool(grid["all_exact_best_response_checks_pass"].all()),
        "distinct_final_routes": sorted(grid["final_assignment"].unique().tolist()),
        "original_adaptive": {
            "route": original_adaptive["final_assignment"],
            "N_eff": original_adaptive["final_effective_environments"],
            "effective_fraction": original_adaptive["final_effective_fraction"],
            "maximum_weight": original_adaptive["final_maximum_weight"],
            "final_survival": original_adaptive["final_survival_rate"],
            "final_worst_regret": original_adaptive["final_worst_regret"],
        },
        "original_static": {
            "route": original_static["final_assignment"],
            "final_survival": original_static["final_survival_rate"],
            "final_worst_regret": original_static["final_worst_regret"],
        },
        "validation_selected_genuine_adaptive": {
            "run_id": genuine_row["run_id"],
            "route": genuine_row["final_assignment"],
            "validation_survival": genuine_row["validation_survival_rate"],
            "validation_worst_regret": genuine_row["validation_worst_regret"],
            "final_survival": genuine_row["final_survival_rate"],
            "final_worst_regret": genuine_row["final_worst_regret"],
        },
        "validation_selected_static": {
            "run_id": static_row["run_id"],
            "route": static_row["final_assignment"],
            "validation_survival": static_row["validation_survival_rate"],
            "validation_worst_regret": static_row["validation_worst_regret"],
            "final_survival": static_row["final_survival_rate"],
            "final_worst_regret": static_row["final_worst_regret"],
        },
        "genuine_adaptive_beats_selected_static_on_final": bool(
            (genuine_row["final_survival_rate"] > static_row["final_survival_rate"])
            or (
                isclose(genuine_row["final_survival_rate"], static_row["final_survival_rate"])
                and genuine_row["final_worst_regret"] < static_row["final_worst_regret"] - 1e-12
            )
        ),
        "rho_pairwise": {
            "comparisons": len(rho_table),
            "route_changes": int(rho_table["route_changed"].sum()),
            "validation_worst_regret_improved": int((rho_table["validation_worst_regret_improvement"] > 1e-12).sum()),
            "validation_worst_regret_worsened": int((rho_table["validation_worst_regret_improvement"] < -1e-12).sum()),
            "final_worst_regret_improved": int((rho_table["final_worst_regret_improvement"] > 1e-12).sum()),
            "final_worst_regret_worsened": int((rho_table["final_worst_regret_improvement"] < -1e-12).sum()),
        },
        "output_hashes": {
            "policy_comparison": sha256_file(policy_path),
            "route_catalog": sha256_file(route_path),
            "factor_summary": sha256_file(factor_path),
            "rho_pairwise": sha256_file(rho_path),
            "correlations": sha256_file(correlation_path),
            "adaptive_eligibility_supplement": sha256_file(eligibility_path),
        },
    }
    write_json(tables / "evolution_diagnostics.json", diagnostics)
    print(json.dumps(diagnostics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
