"""Composite operators: all_of, any_of, none_of with three-valued logic.

Short-circuit semantics per docs/specs/eval-trace.md:
- all_of: any child false -> false (short-circuit); any unknown with no false -> unknown; all true -> true.
- any_of: any child true -> true (short-circuit); any unknown with no true -> unknown; all false -> false.
- none_of: equivalent to NOT any_of. any child true -> false; any unknown with no true -> unknown; all false -> true.
"""

from __future__ import annotations

from typing import Any, Callable


def eval_all_of(
    children_results: list[str],
) -> tuple[str, bool]:
    """Evaluate all_of composite.

    Returns (result, short_circuited).
    Empty list -> true (per predicate-catalog.yaml empty_semantics).
    """
    if not children_results:
        return "true", False

    has_unknown = False
    for r in children_results:
        if r == "false":
            return "false", True  # short-circuited if not the last
        if r == "unknown":
            has_unknown = True

    if has_unknown:
        return "unknown", False
    return "true", False


def eval_any_of(
    children_results: list[str],
) -> tuple[str, bool]:
    """Evaluate any_of composite.

    Returns (result, short_circuited).
    Empty list -> false (per predicate-catalog.yaml empty_semantics).
    """
    if not children_results:
        return "false", False

    has_unknown = False
    for r in children_results:
        if r == "true":
            return "true", True
        if r == "unknown":
            has_unknown = True

    if has_unknown:
        return "unknown", False
    return "false", False


def eval_none_of(
    children_results: list[str],
) -> tuple[str, bool]:
    """Evaluate none_of composite (NOT any_of).

    Returns (result, short_circuited).
    Empty list -> true (per predicate-catalog.yaml empty_semantics).
    """
    if not children_results:
        return "true", False

    has_unknown = False
    for r in children_results:
        if r == "true":
            return "false", True
        if r == "unknown":
            has_unknown = True

    if has_unknown:
        return "unknown", False
    return "true", False
