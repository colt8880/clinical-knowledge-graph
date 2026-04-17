"""Content-addressed cache for arm outputs and judge scores.

Cache key: (fixture_path, arm_id, prompt_hash, context_hash, model_version).
When any component changes, the cache entry invalidates.

Storage layout:
  evals/fixtures/<guideline>/<id>/arms/<arm>/
    output.json     — the arm's raw output
    meta.json       — hash inputs for invalidation
    scores.json     — judge scores (separate cache, keyed on output + rubric version)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def compute_hash(content: str) -> str:
    """SHA-256 hash of a string, truncated to 16 hex chars for readability."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def cache_key(
    fixture_path: str,
    arm_id: str,
    prompt_template: str,
    context: str,
    model_version: str,
) -> dict[str, str]:
    """Build the cache key components and their hashes."""
    return {
        "fixture_path": fixture_path,
        "arm_id": arm_id,
        "prompt_hash": compute_hash(prompt_template),
        "context_hash": compute_hash(context),
        "model_version": model_version,
    }


def _arm_dir(fixture_dir: Path, arm_id: str) -> Path:
    """Return the cache directory for a specific arm's output."""
    return fixture_dir / "arms" / arm_id


def is_cache_valid(fixture_dir: Path, arm_id: str, key: dict[str, str]) -> bool:
    """Check if a cached arm output exists and matches the current key."""
    arm_path = _arm_dir(fixture_dir, arm_id)
    meta_path = arm_path / "meta.json"
    output_path = arm_path / "output.json"

    if not meta_path.exists() or not output_path.exists():
        return False

    try:
        stored_meta = json.loads(meta_path.read_text())
        stored_key = stored_meta.get("cache_key", {})
        return stored_key == key
    except (json.JSONDecodeError, OSError):
        return False


def read_cached_output(fixture_dir: Path, arm_id: str) -> dict[str, Any] | None:
    """Read a cached arm output if it exists."""
    output_path = _arm_dir(fixture_dir, arm_id) / "output.json"
    if not output_path.exists():
        return None
    try:
        return json.loads(output_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(
    fixture_dir: Path,
    arm_id: str,
    key: dict[str, str],
    output: dict[str, Any],
) -> None:
    """Write an arm output and its cache key metadata."""
    arm_path = _arm_dir(fixture_dir, arm_id)
    arm_path.mkdir(parents=True, exist_ok=True)

    meta = {"cache_key": key}
    (arm_path / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n"
    )
    (arm_path / "output.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )


def is_score_cache_valid(
    fixture_dir: Path,
    arm_id: str,
    rubric_version: str,
    judge_model: str,
) -> bool:
    """Check if cached scores exist and match the current rubric + judge model."""
    scores_path = _arm_dir(fixture_dir, arm_id) / "scores.json"
    if not scores_path.exists():
        return False

    try:
        stored = json.loads(scores_path.read_text())
        return (
            stored.get("rubric_version") == rubric_version
            and stored.get("judge_model") == judge_model
        )
    except (json.JSONDecodeError, OSError):
        return False


def read_cached_scores(fixture_dir: Path, arm_id: str) -> dict[str, Any] | None:
    """Read cached judge scores if they exist."""
    scores_path = _arm_dir(fixture_dir, arm_id) / "scores.json"
    if not scores_path.exists():
        return None
    try:
        return json.loads(scores_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def write_scores(
    fixture_dir: Path,
    arm_id: str,
    scores: dict[str, Any],
    rubric_version: str,
    judge_model: str,
) -> None:
    """Write judge scores with rubric version metadata."""
    arm_path = _arm_dir(fixture_dir, arm_id)
    arm_path.mkdir(parents=True, exist_ok=True)

    scores_data = {
        "rubric_version": rubric_version,
        "judge_model": judge_model,
        **scores,
    }
    (arm_path / "scores.json").write_text(
        json.dumps(scores_data, indent=2, sort_keys=True) + "\n"
    )
