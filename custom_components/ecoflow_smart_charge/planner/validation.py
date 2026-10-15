"""Strict scalar/time predicates shared by the pure core."""

from datetime import datetime
from math import isfinite


def number(value: object) -> bool:
    return isinstance(value, (float, int)) and not isinstance(value, bool) and isfinite(value)


def aware(value: object) -> bool:
    return (
        isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
    )
