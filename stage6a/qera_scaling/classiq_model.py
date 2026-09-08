"""Variable-width Classiq QAOA model; synthesis and execution live elsewhere."""

from collections.abc import Sequence
from typing import Any, Callable

from classiq import *  # noqa: F403 - documented Qmod import style

from qera_scaling.qubo import ScalingEnergySpec


def make_classical_cost(
    spec: ScalingEnergySpec,
) -> Callable[[Sequence[int]], float]:
    def cost(routes: Sequence[int]) -> float:
        return spec.transformed_energy(routes)

    return cost


def make_qmod_cost(spec: ScalingEnergySpec) -> Callable[[Any], Any]:
    constant = (spec.qubo.offset - spec.phase_offset) / spec.phase_scale
    linear = tuple(value / spec.phase_scale for value in spec.qubo.linear)
    quadratic = tuple(
        (left, right, value / spec.phase_scale)
        for (left, right), value in sorted(spec.qubo.quadratic.items())
    )

    def cost(routes: Any) -> Any:
        value = constant
        for index, coefficient in enumerate(linear):
            value = value + coefficient * routes[index]
        for left, right, coefficient in quadratic:
            value = value + coefficient * routes[left] * routes[right]
        return value

    return cost


def build_qaoa_main(spec: ScalingEnergySpec, depth: int = 1):
    """Build the frozen one-hot-penalty, transverse-X QAOA at variable width."""

    if depth < 1:
        raise ValueError("QAOA depth must be positive")
    variable_count = len(spec.qubo.linear)
    qmod_cost = make_qmod_cost(spec)

    @qperm  # noqa: F405
    def cost_layer(
        gamma: CReal,  # noqa: F405
        routes: Const[QArray[QBit, variable_count]],  # noqa: F405
    ) -> None:
        phase(-qmod_cost(routes), gamma)  # noqa: F405

    @qfunc  # noqa: F405
    def mixer_layer(
        beta: CReal,  # noqa: F405
        routes: QArray[QBit, variable_count],  # noqa: F405
    ) -> None:
        apply_to_all(lambda qubit: RX(beta, qubit), routes)  # noqa: F405

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
        hadamard_transform(routes)  # noqa: F405
        qaoa_ansatz(params, routes)

    return main


def create_qmod(spec: ScalingEnergySpec, depth: int = 1) -> str:
    return create_model(build_qaoa_main(spec, depth))  # noqa: F405
