from qera.adaptive import run_adaptive
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
