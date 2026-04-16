"""Unit tests for composite operators: all_of, any_of, none_of with three-valued logic."""

from __future__ import annotations

from app.evaluator.predicates.composites import eval_all_of, eval_any_of, eval_none_of


class TestAllOf:
    def test_all_true(self):
        result, sc = eval_all_of(["true", "true", "true"])
        assert result == "true"
        assert sc is False

    def test_one_false_short_circuits(self):
        result, sc = eval_all_of(["true", "false"])
        assert result == "false"
        assert sc is True

    def test_unknown_with_no_false(self):
        result, sc = eval_all_of(["true", "unknown", "true"])
        assert result == "unknown"
        assert sc is False

    def test_false_overrides_unknown(self):
        result, sc = eval_all_of(["unknown", "false"])
        assert result == "false"
        assert sc is True

    def test_empty_is_true(self):
        result, sc = eval_all_of([])
        assert result == "true"
        assert sc is False


class TestAnyOf:
    def test_one_true_short_circuits(self):
        result, sc = eval_any_of(["false", "true"])
        assert result == "true"
        assert sc is True

    def test_all_false(self):
        result, sc = eval_any_of(["false", "false"])
        assert result == "false"
        assert sc is False

    def test_unknown_with_no_true(self):
        result, sc = eval_any_of(["false", "unknown"])
        assert result == "unknown"
        assert sc is False

    def test_true_overrides_unknown(self):
        result, sc = eval_any_of(["unknown", "true"])
        assert result == "true"
        assert sc is True

    def test_empty_is_false(self):
        result, sc = eval_any_of([])
        assert result == "false"
        assert sc is False


class TestNoneOf:
    def test_all_false(self):
        result, sc = eval_none_of(["false", "false"])
        assert result == "true"
        assert sc is False

    def test_one_true_short_circuits_to_false(self):
        result, sc = eval_none_of(["false", "true"])
        assert result == "false"
        assert sc is True

    def test_unknown_with_no_true(self):
        result, sc = eval_none_of(["false", "unknown"])
        assert result == "unknown"
        assert sc is False

    def test_empty_is_true(self):
        result, sc = eval_none_of([])
        assert result == "true"
        assert sc is False
