"""Shared comparison utility for predicates that compare numeric values."""

from __future__ import annotations


def compare_value(value: float, comparator: str, threshold: float) -> bool:
    """Apply a comparator to a value and threshold.

    Supports: eq, ne, gt, lt, gte, lte.
    """
    if comparator == "eq":
        return value == threshold
    elif comparator == "ne":
        return value != threshold
    elif comparator == "gt":
        return value > threshold
    elif comparator == "lt":
        return value < threshold
    elif comparator == "gte":
        return value >= threshold
    elif comparator == "lte":
        return value <= threshold
    raise ValueError(f"Unknown comparator: {comparator}")
