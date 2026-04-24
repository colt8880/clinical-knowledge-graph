"""Braintrust-native eval runner for the Clinical Knowledge Graph.

Usage:
    cd evals
    uv run python -m harness --all --run v1-thesis
    uv run python -m harness --arm c --fixture cross-domain/case-04
    uv run python -m harness --scorecard --run v1-thesis
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from harness.arms import vanilla, flat_rag, graph_context
from harness.config import ARM_IDS, ARM_MODEL, RUBRIC_VERSION, RESULTS_ROOT
from harness.fixtures import load_dataset
from harness.judge import clinical_scorer


def _task_arm_a(input: dict[str, Any]) -> dict[str, Any]:
    """Arm A: PatientContext only (vanilla LLM)."""
    return vanilla.run(
        input,
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )


def _task_arm_b(input: dict[str, Any]) -> dict[str, Any]:
    """Arm B: PatientContext + flat RAG chunks."""
    return flat_rag.run(
        input,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
    )


# Module-level API base URL, set by run_eval() before Eval() calls.
_arm_c_api_base = "http://localhost:8000"


def _task_arm_c(input: dict[str, Any]) -> dict[str, Any]:
    """Arm C: PatientContext + graph context + convergence."""
    return graph_context.run(
        input,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        api_base=_arm_c_api_base,
    )


TASK_MAP = {
    "a": _task_arm_a,
    "b": _task_arm_b,
    "c": _task_arm_c,
}


def run_eval(
    arms: list[str],
    fixture_filter: str | None = None,
    run_name: str = "v1-thesis",
    api_base: str = "http://localhost:8000",
    trial_count: int = 1,
) -> None:
    """Run the eval harness via Braintrust Eval(), one experiment per arm."""
    from braintrust import Eval

    dataset = load_dataset(fixture_filter)
    if not dataset:
        print("No fixtures found.", file=sys.stderr)
        sys.exit(1)

    print(f"Dataset: {len(dataset)} fixtures")
    print(f"Arms: {', '.join(a.upper() for a in arms)}")
    print(f"Trial count: {trial_count}")
    print()

    global _arm_c_api_base
    _arm_c_api_base = api_base

    for arm_id in arms:
        experiment_name = f"{run_name}-arm-{arm_id}"
        print(f"--- Running Arm {arm_id.upper()} as experiment '{experiment_name}' ---")

        task_fn = TASK_MAP[arm_id]

        Eval(
            "clinical-knowledge-graph",
            experiment_name=experiment_name,
            data=dataset,
            task=task_fn,
            scores=[clinical_scorer],
            metadata={
                "arm": arm_id,
                "model": ARM_MODEL,
                "rubric_version": RUBRIC_VERSION,
            },
            trial_count=trial_count,
        )

        print(f"--- Arm {arm_id.upper()} complete ---")
        print()


def run_scorecard(
    run_name: str,
    output_dir: Path | None = None,
    verbose: bool = False,
) -> None:
    """Generate scorecard from Braintrust experiment results."""
    from harness.scorecard import build_scorecard, fetch_from_braintrust
    from harness.report import write_report, write_readme

    import subprocess

    all_run_results = fetch_from_braintrust(run_name, verbose=verbose)
    if not all_run_results or not any(all_run_results):
        print("No results found for run name:", run_name, file=sys.stderr)
        sys.exit(1)

    scorecard = build_scorecard(all_run_results, run_name=run_name)

    out = output_dir or (RESULTS_ROOT / "v1-thesis")
    md_path, json_path = write_report(scorecard, out)

    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        ).stdout.strip() or "unknown"
    except Exception:
        sha = "unknown"

    readme_path = write_readme(scorecard, out, commit_sha=sha)

    print(f"Scorecard written to:")
    print(f"  {md_path}")
    print(f"  {json_path}")
    print(f"  {readme_path}")

    thesis = scorecard["thesis_gate"]
    print()
    print(f"THESIS GATE: {thesis['result']}")
    if thesis.get("margin") is not None:
        print(f"  Arm B composite (multi-gl): {thesis['arm_b_composite']}")
        print(f"  Arm C composite (multi-gl): {thesis['arm_c_composite']}")
        print(f"  Margin (C - B): {thesis['margin']}")
        print(f"  Required: >= {thesis['required_margin']}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Clinical Knowledge Graph eval harness (Braintrust-native)",
        prog="python -m harness",
    )
    parser.add_argument("--fixture", type=str, default=None,
                        help="Run a specific fixture (e.g., statins/01-high-risk-55m-smoker)")
    parser.add_argument("--arm", type=str, choices=["a", "b", "c"], default=None,
                        help="Run a specific arm only")
    parser.add_argument("--guideline", type=str, default=None,
                        help="Run all fixtures for a guideline (e.g., cholesterol)")
    parser.add_argument("--all", action="store_true",
                        help="Run all fixtures with all arms")
    parser.add_argument("--run", type=str, default="v1-thesis",
                        help="Run name (used in Braintrust experiment names)")
    parser.add_argument("--api-base", type=str, default="http://localhost:8000",
                        help="Base URL for the evaluator API (Arm C)")
    parser.add_argument("--trial-count", type=int, default=1,
                        help="Number of trials per input for self-consistency (default: 1)")
    parser.add_argument("--scorecard", action="store_true",
                        help="Generate scorecard from existing Braintrust results (no new runs)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory for scorecard files")
    parser.add_argument("--verbose", action="store_true",
                        help="Show fetch diagnostics (total/scored/dropped row counts)")

    args = parser.parse_args()

    if args.scorecard:
        output_dir = Path(args.output_dir) if args.output_dir else None
        run_scorecard(args.run, output_dir, verbose=args.verbose)
        return

    if not args.all and not args.fixture and not args.guideline:
        parser.error("Specify --fixture <path>, --guideline <name>, or --all")

    if args.guideline:
        fixture_filter = f"_guideline:{args.guideline}"
    elif args.all:
        fixture_filter = None
    else:
        fixture_filter = args.fixture

    arms = [args.arm] if args.arm else list(ARM_IDS)

    run_eval(
        arms=arms,
        fixture_filter=fixture_filter,
        run_name=args.run,
        api_base=args.api_base,
        trial_count=args.trial_count,
    )


if __name__ == "__main__":
    main()
