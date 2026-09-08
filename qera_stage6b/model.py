"""Classiq models for the Stage 6B one-hot-preserving QAOA track.

This module contains modeling only. Synthesis, execution, result processing, and
circuit-resource analysis are intentionally kept in separate modules/scripts.
"""

from classiq import *  # noqa: F403 - Classiq's documented Qmod import style

from qera_scaling.classiq_model import make_qmod_cost
from qera_scaling.qubo import ScalingEnergySpec


PATHS_PER_DEMAND = 3


def _validate_dimensions(variable_count: int, demand_count: int) -> None:
    if demand_count < 1:
        raise ValueError("demand_count must be positive")
    if variable_count != demand_count * PATHS_PER_DEMAND:
        raise ValueError("Stage 6B requires exactly three route bits per demand")


def build_single_demand_mixer_main(initial_route: int):
    """Return a one-demand, basis-state XY-mixer validation model.

    The classical parameter ``beta`` is the Hamiltonian evolution coefficient.
    For each route pair we apply RXX(2 beta) and RYY(2 beta), which together
    implement exp[-i beta (XX + YY)] under Classiq's documented rotation
    convention. Each pair factor, and therefore their product, preserves Hamming
    weight exactly.
    """

    if initial_route not in range(PATHS_PER_DEMAND):
        raise ValueError("initial_route must be 0, 1, or 2")

    @qfunc  # noqa: F405
    def one_hot_mixer(
        beta: CReal,  # noqa: F405
        routes: QArray[QBit, PATHS_PER_DEMAND],  # noqa: F405
    ) -> None:
        RXX(2.0 * beta, [routes[0], routes[1]])  # noqa: F405
        RYY(2.0 * beta, [routes[0], routes[1]])  # noqa: F405
        RXX(2.0 * beta, [routes[1], routes[2]])  # noqa: F405
        RYY(2.0 * beta, [routes[1], routes[2]])  # noqa: F405
        RXX(2.0 * beta, [routes[0], routes[2]])  # noqa: F405
        RYY(2.0 * beta, [routes[0], routes[2]])  # noqa: F405

    @qfunc  # noqa: F405
    def main(
        beta: CReal,  # noqa: F405
        routes: Output[QArray[QBit, PATHS_PER_DEMAND]],  # noqa: F405
    ) -> None:
        allocate(routes)  # noqa: F405
        X(routes[initial_route])  # noqa: F405
        one_hot_mixer(beta, routes)

    return main


def build_initial_state_main(demand_count: int):
    """Return a model that prepares an independent W/Dicke(3,1) per demand."""

    variable_count = demand_count * PATHS_PER_DEMAND
    _validate_dimensions(variable_count, demand_count)

    @qfunc  # noqa: F405
    def main(
        routes: Output[QArray[QBit, variable_count]],  # noqa: F405
    ) -> None:
        allocate(routes)  # noqa: F405
        for demand in range(demand_count):
            start = demand * PATHS_PER_DEMAND
            prepare_dicke_state(1, routes[start : start + PATHS_PER_DEMAND])  # noqa: F405

    return main


def build_constrained_qaoa_main(
    spec: ScalingEnergySpec,
    demand_count: int,
    depth: int = 1,
):
    """Return the fixed-objective, one-hot-preserving QAOA entry point.

    The frozen Stage 6A cost polynomial is reused verbatim. The only ansatz
    changes are the Dicke(3,1) initialization and the number-conserving XY mixer.
    """

    if depth < 1:
        raise ValueError("QAOA depth must be positive")
    variable_count = len(spec.qubo.linear)
    _validate_dimensions(variable_count, demand_count)
    qmod_cost = make_qmod_cost(spec)

    @qperm  # noqa: F405
    def cost_layer(
        gamma: CReal,  # noqa: F405
        routes: Const[QArray[QBit, variable_count]],  # noqa: F405
    ) -> None:
        phase(-qmod_cost(routes), gamma)  # noqa: F405

    @qfunc  # noqa: F405
    def demand_mixer(
        beta: CReal,  # noqa: F405
        demand_routes: QArray[QBit, PATHS_PER_DEMAND],  # noqa: F405
    ) -> None:
        RXX(2.0 * beta, [demand_routes[0], demand_routes[1]])  # noqa: F405
        RYY(2.0 * beta, [demand_routes[0], demand_routes[1]])  # noqa: F405
        RXX(2.0 * beta, [demand_routes[1], demand_routes[2]])  # noqa: F405
        RYY(2.0 * beta, [demand_routes[1], demand_routes[2]])  # noqa: F405
        RXX(2.0 * beta, [demand_routes[0], demand_routes[2]])  # noqa: F405
        RYY(2.0 * beta, [demand_routes[0], demand_routes[2]])  # noqa: F405

    @qfunc  # noqa: F405
    def mixer_layer(
        beta: CReal,  # noqa: F405
        routes: QArray[QBit, variable_count],  # noqa: F405
    ) -> None:
        for demand in range(demand_count):
            start = demand * PATHS_PER_DEMAND
            demand_mixer(beta, routes[start : start + PATHS_PER_DEMAND])

    @qfunc  # noqa: F405
    def qaoa_ansatz(
        params: CArray[CReal, depth * 2],  # noqa: F405
        routes: QArray[QBit, variable_count],  # noqa: F405
    ) -> None:
        repeat(  # noqa: F405
            depth,
            lambda layer: [
                cost_layer(params[layer], routes),
                mixer_layer(params[depth + layer], routes),
            ],
        )

    @qfunc  # noqa: F405
    def main(
        params: CArray[CReal, depth * 2],  # noqa: F405
        routes: Output[QArray[QBit, variable_count]],  # noqa: F405
    ) -> None:
        allocate(routes)  # noqa: F405
        for demand in range(demand_count):
            start = demand * PATHS_PER_DEMAND
            prepare_dicke_state(1, routes[start : start + PATHS_PER_DEMAND])  # noqa: F405
        qaoa_ansatz(params, routes)

    return main


def create_constrained_qmod(
    spec: ScalingEnergySpec,
    demand_count: int,
    depth: int = 1,
) -> str:
    """Serialize the Stage 6B model locally without synthesis or execution."""

    return create_model(  # noqa: F405
        build_constrained_qaoa_main(spec, demand_count, depth)
    )
