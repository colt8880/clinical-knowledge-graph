"""Unit tests for the guidelines query module."""

import pytest

from app.queries.guidelines_query import _compute_seed_hash, _SEED_HASHES


def test_seed_hashes_all_computed():
    """All three seed files should have non-None hashes."""
    for gid, h in _SEED_HASHES.items():
        assert h is not None, f"Seed hash is None for {gid}"
        assert len(h) == 64, f"Seed hash wrong length for {gid}"


def test_seed_hash_deterministic():
    """Computing the same file twice yields the same hash."""
    h1 = _compute_seed_hash("statins.cypher")
    h2 = _compute_seed_hash("statins.cypher")
    assert h1 == h2


def test_seed_hash_nonexistent_file():
    """A nonexistent file returns None."""
    assert _compute_seed_hash("nonexistent.cypher") is None
