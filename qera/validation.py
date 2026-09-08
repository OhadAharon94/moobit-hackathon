"""Strict scalar validation shared by evaluators and sample decoding."""

from __future__ import annotations

from math import isfinite
from numbers import Real
from typing import Any


def validated_integer(value: Any, label: str) -> int:
    """Return an integer-valued real without silently truncating fractions."""

    if not isinstance(value, Real):
        raise ValueError(f"{label} must be a real integer value, got {value!r}")
    numeric = float(value)
    if not isfinite(numeric) or not numeric.is_integer():
        raise ValueError(f"{label} must be finite and integral, got {value!r}")
    return int(numeric)
