"""Unit tests for cache key hashing and invalidation."""

import json
import tempfile
from pathlib import Path

import pytest

from harness.cache import (
    cache_key,
    compute_hash,
    is_cache_valid,
    is_score_cache_valid,
    read_cached_output,
    read_cached_scores,
    write_cache,
    write_scores,
)


@pytest.fixture
def fixture_dir():
    """Create a temporary fixture directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestComputeHash:
    def test_deterministic(self):
        assert compute_hash("hello") == compute_hash("hello")

    def test_different_inputs_different_hashes(self):
        assert compute_hash("hello") != compute_hash("world")

    def test_returns_16_hex_chars(self):
        h = compute_hash("test")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)


class TestCacheKey:
    def test_builds_key_with_all_components(self):
        key = cache_key(
            fixture_path="statins/01-high-risk",
            arm_id="a",
            prompt_template="You are a doctor...",
            context='{"patient": {}}',
            model_version="claude-sonnet-4-6-20250514",
        )
        assert key["fixture_path"] == "statins/01-high-risk"
        assert key["arm_id"] == "a"
        assert key["model_version"] == "claude-sonnet-4-6-20250514"
        assert "prompt_hash" in key
        assert "context_hash" in key

    def test_different_prompt_different_key(self):
        key1 = cache_key("fix", "a", "prompt1", "ctx", "model")
        key2 = cache_key("fix", "a", "prompt2", "ctx", "model")
        assert key1["prompt_hash"] != key2["prompt_hash"]

    def test_different_context_different_key(self):
        key1 = cache_key("fix", "a", "prompt", "ctx1", "model")
        key2 = cache_key("fix", "a", "prompt", "ctx2", "model")
        assert key1["context_hash"] != key2["context_hash"]

    def test_same_inputs_same_key(self):
        key1 = cache_key("fix", "a", "prompt", "ctx", "model")
        key2 = cache_key("fix", "a", "prompt", "ctx", "model")
        assert key1 == key2


class TestWriteAndReadCache:
    def test_write_and_read(self, fixture_dir):
        key = cache_key("fix/01", "a", "prompt", "ctx", "model-v1")
        output = {"arm": "a", "parsed": {"actions": []}, "raw_output": "{}"}

        write_cache(fixture_dir, "a", key, output)

        cached = read_cached_output(fixture_dir, "a")
        assert cached is not None
        assert cached["arm"] == "a"

    def test_cache_validity_matches(self, fixture_dir):
        key = cache_key("fix/01", "a", "prompt", "ctx", "model-v1")
        output = {"arm": "a"}

        write_cache(fixture_dir, "a", key, output)

        assert is_cache_valid(fixture_dir, "a", key) is True

    def test_cache_invalid_on_prompt_change(self, fixture_dir):
        key1 = cache_key("fix/01", "a", "prompt-v1", "ctx", "model")
        output = {"arm": "a"}
        write_cache(fixture_dir, "a", key1, output)

        key2 = cache_key("fix/01", "a", "prompt-v2", "ctx", "model")
        assert is_cache_valid(fixture_dir, "a", key2) is False

    def test_cache_invalid_on_context_change(self, fixture_dir):
        key1 = cache_key("fix/01", "a", "prompt", "ctx-v1", "model")
        write_cache(fixture_dir, "a", key1, {"arm": "a"})

        key2 = cache_key("fix/01", "a", "prompt", "ctx-v2", "model")
        assert is_cache_valid(fixture_dir, "a", key2) is False

    def test_cache_invalid_on_model_change(self, fixture_dir):
        key1 = cache_key("fix/01", "a", "prompt", "ctx", "model-v1")
        write_cache(fixture_dir, "a", key1, {"arm": "a"})

        key2 = cache_key("fix/01", "a", "prompt", "ctx", "model-v2")
        assert is_cache_valid(fixture_dir, "a", key2) is False

    def test_no_cache_returns_none(self, fixture_dir):
        assert read_cached_output(fixture_dir, "a") is None

    def test_no_cache_invalid(self, fixture_dir):
        key = cache_key("fix/01", "a", "prompt", "ctx", "model")
        assert is_cache_valid(fixture_dir, "a", key) is False


class TestScoreCache:
    def test_write_and_read_scores(self, fixture_dir):
        scores = {
            "rubric_scores": {
                "completeness": {"score": 4},
                "composite": 4.0,
            }
        }
        write_scores(fixture_dir, "a", scores, "v1", "opus-4.6")

        cached = read_cached_scores(fixture_dir, "a")
        assert cached is not None
        assert cached["rubric_version"] == "v1"
        assert cached["judge_model"] == "opus-4.6"

    def test_score_cache_validity(self, fixture_dir):
        scores = {"rubric_scores": {}}
        write_scores(fixture_dir, "a", scores, "v1", "opus-4.6")

        assert is_score_cache_valid(fixture_dir, "a", "v1", "opus-4.6") is True

    def test_score_cache_invalid_on_rubric_change(self, fixture_dir):
        scores = {"rubric_scores": {}}
        write_scores(fixture_dir, "a", scores, "v1", "opus-4.6")

        assert is_score_cache_valid(fixture_dir, "a", "v2", "opus-4.6") is False

    def test_score_cache_invalid_on_judge_change(self, fixture_dir):
        scores = {"rubric_scores": {}}
        write_scores(fixture_dir, "a", scores, "v1", "opus-4.6")

        assert is_score_cache_valid(fixture_dir, "a", "v1", "opus-5.0") is False

    def test_no_scores_returns_none(self, fixture_dir):
        assert read_cached_scores(fixture_dir, "a") is None
