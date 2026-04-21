"""CLI for generating scorecards from harness results.

Usage:
    cd evals
    uv run python -m harness.scorecard_cli --run v1-thesis
    uv run python -m harness.scorecard --run v1-thesis
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from harness.config import RESULTS_ROOT
from harness.scorecard import build_scorecard
from harness.report import write_report, write_readme


def _find_latest_results() -> Path | None:
    """Find the most recent results directory."""
    if not RESULTS_ROOT.exists():
        return None
    dirs = sorted(RESULTS_ROOT.iterdir(), reverse=True)
    for d in dirs:
        if d.is_dir() and (d / "results.json").exists():
            return d
    return None


def _load_results(results_dir: Path) -> list[dict]:
    """Load the results list from a results.json file."""
    results_file = results_dir / "results.json"
    if not results_file.exists():
        print(f"No results.json found in {results_dir}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(results_file.read_text())
    return data.get("entries", [])


def _entries_to_run_results(entries: list[dict]) -> list[dict]:
    """Convert BraintrustLogger entries to the format scorecard expects."""
    results = []
    for entry in entries:
        scores = entry.get("scores", {})
        results.append({
            "fixture": entry["fixture_id"],
            "arm": entry["arm_id"],
            "composite": scores.get("composite", 0),
            "scores": {
                "rubric_scores": scores,
            },
        })
    return results


def _get_commit_sha() -> str:
    """Get the current git commit SHA."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate scorecard from eval harness results",
        prog="python -m harness.scorecard",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        help="Run name (used to find results and name the scorecard)",
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="Explicit path to a results directory containing results.json",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for scorecard files (default: evals/results/v1-thesis/)",
    )
    parser.add_argument(
        "--braintrust-url",
        type=str,
        default=None,
        help="Braintrust experiment URL to reference in the README",
    )

    args = parser.parse_args()

    # Find the results
    if args.results_dir:
        results_dir = Path(args.results_dir)
    else:
        results_dir = _find_latest_results()

    if results_dir is None or not results_dir.exists():
        print("No results directory found. Run the harness first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading results from: {results_dir}")

    entries = _load_results(results_dir)
    if not entries:
        print("No entries found in results.json.", file=sys.stderr)
        sys.exit(1)

    run_results = _entries_to_run_results(entries)
    run_name = args.run or "v1-thesis"

    # Build scorecard (single run — multi-run from runner passes all_run_results)
    scorecard = build_scorecard([run_results], run_name=run_name)

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = RESULTS_ROOT / "v1-thesis"

    # Write outputs
    md_path, json_path = write_report(scorecard, output_dir)
    commit_sha = _get_commit_sha()
    readme_path = write_readme(
        scorecard, output_dir,
        commit_sha=commit_sha,
        braintrust_url=args.braintrust_url,
    )

    print(f"Scorecard written to:")
    print(f"  {md_path}")
    print(f"  {json_path}")
    print(f"  {readme_path}")

    # Print thesis gate result
    thesis = scorecard["thesis_gate"]
    print()
    print(f"THESIS GATE: {thesis['result']}")
    if thesis.get("margin") is not None:
        print(f"  Arm B composite (multi-gl): {thesis['arm_b_composite']}")
        print(f"  Arm C composite (multi-gl): {thesis['arm_c_composite']}")
        print(f"  Margin (C - B): {thesis['margin']}")
        print(f"  Required: >= {thesis['required_margin']}")


if __name__ == "__main__":
    main()
