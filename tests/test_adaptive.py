from qera.adaptive import run_adaptive
from qera.decision_trace import build_decision_trace
from qera.evaluate import Evaluator
from qera.exact import ExactInnerSolver, exact_adaptive_run
from qera.types import SolveStatus


def test_shared_adaptive_loop_matches_reference_exact_cost_run() -> None:
    evaluator = Evaluator()
    shared = run_adaptive(ExactInnerSolver(evaluator), evaluator, "cost")
    reference = exact_adaptive_run(evaluator, "cost")
    assert shared.status == SolveStatus.SUCCESS
    assert [step.result.assignment for step in shared.steps] == [
        record.assignment for record in reference
    ]
    assert [step.request.scenario_weights for step in shared.steps] == [
        record.weights for record in reference
    ]
    assert shared.best_assignment == (0, 1, 1, 2)


def test_shared_adaptive_loop_matches_reference_regret_run() -> None:
    evaluator = Evaluator()
    shared = run_adaptive(ExactInnerSolver(evaluator), evaluator, "regret")
    reference = exact_adaptive_run(evaluator, "regret")
    assert [step.result.assignment for step in shared.steps] == [
        record.assignment for record in reference
    ]


def test_decision_trace_explains_adaptive_pressure() -> None:
    evaluator = Evaluator()
    adaptive = run_adaptive(ExactInnerSolver(evaluator), evaluator, "cost")
    summary = {
        "source_runs": ["exact-0", "exact-1", "exact-2"],
        "steps": [
            {
                "request": {
                    "scenario_weights": step.request.scenario_weights,
                    "seed": step.request.seed,
                },
                "result": {
                    "assignment": step.result.assignment,
                    "metadata": step.result.metadata,
                },
                "regrets": step.regrets,
                "best_so_far": step.best_so_far,
            }
            for step in adaptive.steps
        ],
    }
    rows = build_decision_trace(summary)
    assert len(rows) == 3
    assert rows[0]["stressed_scenario"] == "degradation"
    assert "degradation 0.333→0.407" in rows[0]["update_explanation"]
    assert rows[-1]["selected_route"] == "[0, 1, 1, 2]"
    assert rows[-1]["update_explanation"].startswith("Final solve")
