"""Classiq QAOA model construction; no synthesis or execution calls live here."""

from collections.abc import Sequence
from typing import Any, Callable

from classiq import *  # noqa: F403 - Classiq's documented Qmod import style

from qera.config import QAOA_DEPTH, VARIABLE_COUNT
from qera.energy import EnergySpec


def make_classical_cost(spec: EnergySpec) -> Callable[[Sequence[int]], float]:
    """Return the optimizer/reference form of the transformed QAOA energy."""

    def cost(routes: Sequence[int]) -> float:
        return spec.transformed_energy(routes)

    return cost


def make_qmod_cost(spec: EnergySpec) -> Callable[[Any], Any]:
    """Build the same transformed polynomial for a QArray or classical bit list."""

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


def build_qaoa_main(spec: EnergySpec, depth: int = QAOA_DEPTH):
    """Return one parameterized Qmod entry point for a base-energy QAOA model."""

    if depth < 1:
        raise ValueError("QAOA depth must be positive")
    if spec.energy_mode != "base":
        raise NotImplementedError(
            "digital capacity alignment is intentionally deferred to Stage 6"
        )
    qmod_cost = make_qmod_cost(spec)

    @qperm  # noqa: F405
    def cost_layer(
        gamma: CReal, routes: Const[QArray[QBit, VARIABLE_COUNT]]  # noqa: F405
    ) -> None:
        phase(-qmod_cost(routes), gamma)  # noqa: F405

    @qfunc  # noqa: F405
    def mixer_layer(beta: CReal, routes: QArray[QBit, VARIABLE_COUNT]) -> None:  # noqa: F405
        apply_to_all(lambda qubit: RX(beta, qubit), routes)  # noqa: F405

    @qfunc  # noqa: F405
    def qaoa_ansatz(
        params: CArray[CReal, depth * 2],  # noqa: F405
        routes: QArray[QBit, VARIABLE_COUNT],  # noqa: F405
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
        routes: Output[QArray[QBit, VARIABLE_COUNT]],  # noqa: F405
    ) -> None:
        allocate(routes)  # noqa: F405
        hadamard_transform(routes)  # noqa: F405
        qaoa_ansatz(params, routes)

    return main


def create_qmod(spec: EnergySpec, depth: int = QAOA_DEPTH) -> str:
    """Serialize the model locally without synthesizing or executing it."""

    return create_model(build_qaoa_main(spec, depth))  # noqa: F405
