"""Eval harness runner: orchestrates arm runs per fixture, handles caching.

Usage:
    cd evals
    uv run python -m harness.runner --fixture statins/case-01 --arm a
    uv run python -m harness.runner --all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from harness import cache
from harness.arms import vanilla, flat_rag, graph_context
from harness.braintrust_client import BraintrustLogger
from harness.config import (
    ARM_IDS,
    ARM_MODEL,
    FIXTURES_ROOT,
    RUBRIC_VERSION,
    JUDGE_MODEL,
)
from harness import judge


def discover_fixtures(fixture_filter: str | None = None) -> list[Path]:
    """Discover fixture directories under evals/fixtures/.

    If fixture_filter is set (e.g., "statins/01-high-risk-55m-smoker"),
    return only that fixture. Otherwise return all fixtures that have
    both patient.json and expected-actions.json.
    """
    if fixture_filter:
        fixture_dir = FIXTURES_ROOT / fixture_filter
        if not fixture_dir.exists():
            # Try matching by partial name
            parts = fixture_filter.split("/")
            if len(parts) == 2:
                guideline, case_prefix = parts
                guideline_dir = FIXTURES_ROOT / guideline
                if guideline_dir.exists():
                    for d in sorted(guideline_dir.iterdir()):
                        if d.is_dir() and d.name.startswith(case_prefix):
                            fixture_dir = d
                            break
            if not fixture_dir.exists():
                print(f"Fixture not found: {fixture_filter}", file=sys.stderr)
                sys.exit(1)
        return [fixture_dir]

    # Discover all fixtures
    fixtures: list[Path] = []
    if not FIXTURES_ROOT.exists():
        return fixtures
    for guideline_dir in sorted(FIXTURES_ROOT.iterdir()):
        if not guideline_dir.is_dir() or guideline_dir.name.startswith("."):
            continue
        if guideline_dir.name == "archive":
            continue
        for case_dir in sorted(guideline_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            if (case_dir / "patient.json").exists() and (case_dir / "expected-actions.json").exists():
                fixtures.append(case_dir)
    return fixtures


def load_fixture(fixture_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load patient context and expected actions from a fixture directory."""
    patient = json.loads((fixture_dir / "patient.json").read_text())
    expected = json.loads((fixture_dir / "expected-actions.json").read_text())
    return patient, expected


def fixture_id(fixture_dir: Path) -> str:
    """Return a human-readable fixture ID like 'statins/01-high-risk-55m-smoker'."""
    return f"{fixture_dir.parent.name}/{fixture_dir.name}"


def _get_prompt_template(arm_id: str) -> str:
    """Return the prompt template for a given arm (for cache key hashing)."""
    if arm_id == "a":
        return vanilla.PROMPT_TEMPLATE
    elif arm_id == "b":
        return flat_rag.PROMPT_TEMPLATE
    elif arm_id == "c":
        return graph_context.PROMPT_TEMPLATE
    return ""


def _get_context_string(
    arm_id: str,
    patient_context: dict[str, Any],
) -> str:
    """Build the context string for cache key hashing.

    For Arm A: just the patient context.
    For Arm B: patient context + guideline texts (chunk content may vary).
    For Arm C: patient context (trace output depends on graph version, captured via model version).
    """
    if arm_id == "a":
        return json.dumps(patient_context, sort_keys=True)
    elif arm_id == "b":
        # Include guideline file contents for cache invalidation
        from harness.config import GUIDELINES_ROOT
        guideline_texts = ""
        if GUIDELINES_ROOT.exists():
            for f in sorted(GUIDELINES_ROOT.glob("*.md")):
                guideline_texts += f.read_text()
        return json.dumps(patient_context, sort_keys=True) + guideline_texts
    elif arm_id == "c":
        return json.dumps(patient_context, sort_keys=True)
    return ""


def run_arm(
    arm_id: str,
    fixture_dir: Path,
    patient_context: dict[str, Any],
    force: bool = False,
    api_base: str = "http://localhost:8000",
) -> dict[str, Any]:
    """Run a single arm against a fixture, with caching.

    Returns the arm output (from cache or fresh run).
    """
    fid = fixture_id(fixture_dir)
    prompt_template = _get_prompt_template(arm_id)
    context_string = _get_context_string(arm_id, patient_context)

    key = cache.cache_key(
        fixture_path=fid,
        arm_id=arm_id,
        prompt_template=prompt_template,
        context=context_string,
        model_version=ARM_MODEL,
    )

    # Check cache
    if not force and cache.is_cache_valid(fixture_dir, arm_id, key):
        cached = cache.read_cached_output(fixture_dir, arm_id)
        if cached is not None:
            print(f"  [{arm_id.upper()}] Cache hit for {fid}")
            return cached

    # Run the arm
    print(f"  [{arm_id.upper()}] Running arm {arm_id} on {fid}...")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if arm_id == "a":
        output = vanilla.run(patient_context, api_key=anthropic_key)
    elif arm_id == "b":
        output = flat_rag.run(
            patient_context,
            anthropic_api_key=anthropic_key,
            openai_api_key=openai_key,
        )
    elif arm_id == "c":
        output = graph_context.run(
            patient_context,
            anthropic_api_key=anthropic_key,
            api_base=api_base,
        )
    else:
        raise ValueError(f"Unknown arm: {arm_id}")

    # Write to cache
    cache.write_cache(fixture_dir, arm_id, key, output)
    print(f"  [{arm_id.upper()}] Cached output for {fid}")

    return output


def score_arm(
    arm_id: str,
    fixture_dir: Path,
    patient_context: dict[str, Any],
    arm_output: dict[str, Any],
    expected_actions: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    """Score an arm's output, with caching."""
    fid = fixture_id(fixture_dir)

    if not force and cache.is_score_cache_valid(
        fixture_dir, arm_id, RUBRIC_VERSION, JUDGE_MODEL
    ):
        cached = cache.read_cached_scores(fixture_dir, arm_id)
        if cached is not None:
            print(f"  [{arm_id.upper()}] Score cache hit for {fid}")
            return cached

    print(f"  [{arm_id.upper()}] Scoring arm {arm_id} on {fid}...")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    scores = judge.score(
        patient_context=patient_context,
        arm_output=arm_output,
        expected_actions=expected_actions,
        api_key=anthropic_key,
    )

    cache.write_scores(fixture_dir, arm_id, scores, RUBRIC_VERSION, JUDGE_MODEL)
    return scores


def run_harness(
    fixture_filter: str | None = None,
    arm_filter: str | None = None,
    force: bool = False,
    score_only: bool = False,
    api_base: str = "http://localhost:8000",
) -> dict[str, Any]:
    """Run the full harness: arms + judge across fixtures.

    Returns a summary dict with per-fixture, per-arm results.
    """
    fixtures = discover_fixtures(fixture_filter)
    arms = [arm_filter] if arm_filter else list(ARM_IDS)

    if not fixtures:
        print("No fixtures found with expected-actions.json.", file=sys.stderr)
        sys.exit(1)

    print(f"Running {len(fixtures)} fixture(s) x {len(arms)} arm(s) = {len(fixtures) * len(arms)} runs")
    print()

    logger = BraintrustLogger()
    experiment_name = "statins-baseline"
    if fixture_filter:
        experiment_name = f"eval-{fixture_filter.replace('/', '-')}"
    logger.start_experiment(experiment_name)

    results: list[dict[str, Any]] = []

    for fix_dir in fixtures:
        fid = fixture_id(fix_dir)
        print(f"Fixture: {fid}")

        patient_context, expected_actions = load_fixture(fix_dir)

        for arm_id in arms:
            # Run the arm
            arm_output = run_arm(
                arm_id, fix_dir, patient_context,
                force=force, api_base=api_base,
            )

            # Score the output
            scores = score_arm(
                arm_id, fix_dir, patient_context,
                arm_output, expected_actions, force=force,
            )

            # Log to Braintrust / local
            logger.log_entry(
                fixture_id=fid,
                arm_id=arm_id,
                patient_context=patient_context,
                output=arm_output,
                scores=scores,
                expected_actions=expected_actions,
            )

            composite = scores.get("rubric_scores", {}).get("composite", 0)
            results.append({
                "fixture": fid,
                "arm": arm_id,
                "composite": composite,
                "scores": scores,
            })

        print()

    results_dir = logger.finish_experiment()
    print(f"Results written to: {results_dir}")

    if logger.is_enabled:
        print("Results also logged to Braintrust.")

    return {"results": results, "results_dir": str(results_dir)}


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Clinical Knowledge Graph eval harness",
        prog="python -m harness.runner",
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Run a specific fixture (e.g., statins/01-high-risk-55m-smoker)",
    )
    parser.add_argument(
        "--arm",
        type=str,
        choices=["a", "b", "c"],
        default=None,
        help="Run a specific arm only",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all fixtures with all arms",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run, ignoring cache",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default="http://localhost:8000",
        help="Base URL for the evaluator API (Arm C)",
    )

    args = parser.parse_args()

    if not args.all and not args.fixture:
        parser.error("Specify --fixture <path> or --all")

    fixture_filter = None if args.all else args.fixture

    run_harness(
        fixture_filter=fixture_filter,
        arm_filter=args.arm,
        force=args.force,
        api_base=args.api_base,
    )


if __name__ == "__main__":
    main()
