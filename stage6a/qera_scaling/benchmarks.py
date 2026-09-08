"""Classical controls and scaling records for Stage 6A."""

from __future__ import annotations

import math
import random
from time import perf_counter

from qera_scaling.evaluate import ScalingEvaluator
from qera_scaling.model import Assignment


def shortest_path(evaluator: ScalingEvaluator) -> Assignment:
    instance = evaluator.instance
    links = instance.link_by_edge
    return tuple(
        min(
            range(instance.paths_per_demand),
            key=lambda path_index: sum(
                links[edge].latency
                for edge in instance.path_edges[demand_index][path_index]
            ),
        )
        for demand_index in range(instance.demand_count)
    )


def load_aware_greedy(evaluator: ScalingEvaluator) -> Assignment:
    fallback = shortest_path(evaluator)
    weights = (1.0 / evaluator.instance.scenario_count,) * evaluator.instance.scenario_count
    chosen: list[int] = []
    for demand_index in range(evaluator.instance.demand_count):
        candidates = []
        for path_index in range(evaluator.instance.paths_per_demand):
            route = tuple(chosen + [path_index] + list(fallback[demand_index + 1 :]))
            evaluations = evaluator.evaluate_all(route)
            score = (
                sum(item.overflow for item in evaluations),
                max(item.maximum_utilization for item in evaluations),
                evaluator.weighted_objective(route, weights, "cost"),
                path_index,
            )
            candidates.append((score, path_index))
        chosen.append(min(candidates)[1])
    return tuple(chosen)


def local_search(
    evaluator: ScalingEvaluator, start: Assignment, weights: tuple[float, ...]
) -> tuple[Assignment, int]:
    current = start
    evaluations = 0
    while True:
        candidates = []
        for demand_index in range(evaluator.instance.demand_count):
            for path_index in range(evaluator.instance.paths_per_demand):
                if path_index == current[demand_index]:
                    continue
                route = current[:demand_index] + (path_index,) + current[demand_index + 1 :]
                evaluations += 1
                if evaluator.is_joint_feasible(route):
                    candidates.append(
                        (evaluator.weighted_objective(route, weights, "cost"), route)
                    )
        if not candidates:
            return current, evaluations
        _, best = min(candidates)
        if evaluator.weighted_objective(best, weights, "cost") >= evaluator.weighted_objective(
            current, weights, "cost"
        ) - 1e-12:
            return current, evaluations
        current = best


def simulated_annealing(
    evaluator: ScalingEvaluator,
    weights: tuple[float, ...],
    *,
    seed: int,
    steps: int = 10_000,
) -> tuple[Assignment, int]:
    rng = random.Random(seed)
    current = tuple(
        rng.randrange(evaluator.instance.paths_per_demand)
        for _ in range(evaluator.instance.demand_count)
    )

    def score(route: Assignment) -> float:
        evaluations = evaluator.evaluate_all(route)
        return evaluator.weighted_objective(route, weights, "cost") + 10.0 * sum(
            item.overflow for item in evaluations
        )

    current_score = score(current)
    feasible_best: tuple[float, Assignment] | None = None
    for step in range(steps):
        demand = rng.randrange(evaluator.instance.demand_count)
        choices = [
            value
            for value in range(evaluator.instance.paths_per_demand)
            if value != current[demand]
        ]
        proposal = current[:demand] + (rng.choice(choices),) + current[demand + 1 :]
        proposal_score = score(proposal)
        temperature = max(1e-4, 1.0 - step / steps)
        if proposal_score < current_score or rng.random() < math.exp(
            min(0.0, (current_score - proposal_score) / temperature)
        ):
            current, current_score = proposal, proposal_score
        if evaluator.is_joint_feasible(current):
            key = (evaluator.weighted_objective(current, weights, "cost"), current)
            if feasible_best is None or key < feasible_best:
                feasible_best = key
    if feasible_best is None:
        return load_aware_greedy(evaluator), steps
    return feasible_best[1], steps


def route_metrics(
    evaluator: ScalingEvaluator, assignment: Assignment, weights: tuple[float, ...]
) -> dict:
    regrets = [evaluator.regret(assignment, s) for s in evaluator.instance.scenarios]
    return {
        "assignment": list(assignment),
        "joint_feasible": evaluator.is_joint_feasible(assignment),
        "weighted_cost": evaluator.weighted_objective(assignment, weights, "cost"),
        "worst_case_regret": max(regrets),
        "scenario_regrets": regrets,
        "total_overflow": sum(item.overflow for item in evaluator.evaluate_all(assignment)),
    }


def classical_record(evaluator: ScalingEvaluator, shots: int = 4096) -> dict:
    instance = evaluator.instance
    weights = (1.0 / instance.scenario_count,) * instance.scenario_count
    exact_value, exact_routes, exact_runtime = evaluator.exact_optima(
        weights, "cost", joint_feasible=True
    )
    all_routes = tuple(evaluator.all_assignments())
    minimax_start = perf_counter()
    feasible = [route for route in all_routes if evaluator.is_joint_feasible(route)]
    minimax_value = min(
        max(evaluator.regret(route, s) for s in instance.scenarios) for route in feasible
    )
    minimax_routes = [
        route
        for route in feasible
        if abs(max(evaluator.regret(route, s) for s in instance.scenarios) - minimax_value)
        <= 1e-10
    ]
    minimax_runtime = perf_counter() - minimax_start

    greedy_start = perf_counter()
    greedy_route = load_aware_greedy(evaluator)
    greedy_runtime = perf_counter() - greedy_start
    local_start = perf_counter()
    local_route, local_evaluations = local_search(evaluator, greedy_route, weights)
    local_runtime = perf_counter() - local_start
    anneal_start = perf_counter()
    anneal_route, anneal_evaluations = simulated_annealing(
        evaluator, weights, seed=instance.seed + 211
    )
    anneal_runtime = perf_counter() - anneal_start

    rng = random.Random(instance.seed + 313)
    sampled = [rng.choice(all_routes) for _ in range(shots)]
    random_feasible = [route for route in sampled if evaluator.is_joint_feasible(route)]
    random_best = (
        min(random_feasible, key=lambda route: (evaluator.weighted_objective(route, weights, "cost"), route))
        if random_feasible
        else None
    )
    return {
        "instance_id": instance.instance_id,
        "seed": instance.seed,
        "nodes": len({node for edge in instance.edge_order for node in edge}),
        "edges": len(instance.links),
        "D": instance.demand_count,
        "K": instance.paths_per_demand,
        "S": instance.scenario_count,
        "logical_bits": instance.variable_count,
        "valid_assignments": len(all_routes),
        "exact_status": "OPTIMAL_ENUMERATION",
        "exact_runtime_seconds": exact_runtime,
        "exact_weighted_cost": exact_value,
        "exact_assignments": [list(route) for route in exact_routes],
        "exact_worst_case_regret": minimax_value,
        "exact_minimax_assignments": [list(route) for route in minimax_routes],
        "minimax_runtime_seconds": minimax_runtime,
        "joint_feasible_count": len(feasible),
        "joint_feasible_fraction_valid": len(feasible) / len(all_routes),
        "greedy_runtime_seconds": greedy_runtime,
        "greedy": route_metrics(evaluator, greedy_route, weights),
        "local_search_runtime_seconds": local_runtime,
        "local_search_evaluations": local_evaluations,
        "local_search": route_metrics(evaluator, local_route, weights),
        "simulated_annealing_runtime_seconds": anneal_runtime,
        "simulated_annealing_evaluations": anneal_evaluations,
        "simulated_annealing": route_metrics(evaluator, anneal_route, weights),
        "random_valid_shots": shots,
        "random_valid_feasible_fraction": len(random_feasible) / shots,
        "random_valid_best": (
            route_metrics(evaluator, random_best, weights) if random_best else None
        ),
    }
