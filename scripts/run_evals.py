#!/usr/bin/env python3
"""Evals runner: runs all statin fixtures through the evaluator and reports pass/fail.

Usage:
    python scripts/run_evals.py

Requires:
    - Neo4j running with the statin seed loaded
    - Python venv with ckg-api[dev] installed

Pass/fail criteria (per evals/SPEC.md):
    1. expected_recommendations: every entry appears in the derived recommendation view
    2. expected_trace_contains: every template matches at least one event
    3. must_not_contain: no event matches any template
    4. Determinism: two runs produce identical canonical JSON
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure api/ is on the path
API_DIR = Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(API_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "evals" / "fixtures" / "statins"


def _canonical_json(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _strip_wall_clock(trace: dict) -> dict:
    out = json.loads(json.dumps(trace))
    env = out.get("envelope", {})
    env.pop("started_at", None)
    env.pop("completed_at", None)
    for event in out.get("events", []):
        event.pop("at", None)
        if event.get("type") == "evaluation_completed":
            event["duration_ms"] = 0
    return out


def _partial_match(template: dict, event: dict) -> bool:
    for key, value in template.items():
        if key not in event or event[key] != value:
            return False
    return True


def check_fixture(
    case_name: str,
    trace: dict,
    expected_outcome: dict,
    expected_trace: dict,
) -> list[str]:
    """Check a single fixture. Returns list of failure messages (empty = pass)."""
    failures: list[str] = []

    # 1. expected_recommendations
    recs = trace["recommendations"]
    expected_recs = expected_outcome.get("expected_recommendations", [])
    for exp_rec in expected_recs:
        if not any(_partial_match(exp_rec, r) for r in recs):
            failures.append(f"  Missing expected recommendation: {exp_rec}")
    if len(recs) != len(expected_recs):
        failures.append(f"  Recommendation count mismatch: expected {len(expected_recs)}, got {len(recs)}")

    # 2. expected_trace_contains
    events = trace["events"]
    for template in expected_outcome.get("expected_trace_contains", []):
        if not any(_partial_match(template, e) for e in events):
            failures.append(f"  Missing expected trace event: {template}")

    # 3. must_not_contain
    for template in expected_outcome.get("must_not_contain", []):
        matching = [e for e in events if _partial_match(template, e)]
        if matching:
            failures.append(f"  Forbidden event found: {template}")

    # 4. Golden trace match
    actual = _strip_wall_clock(trace)
    expected = _strip_wall_clock(expected_trace)
    if _canonical_json(actual) != _canonical_json(expected):
        failures.append("  Golden trace mismatch (canonical JSON differs)")

    return failures


async def main() -> int:
    from app.config import settings
    from app.db import init_driver, close_driver
    from app.evaluator.engine import evaluate
    from app.evaluator.graph import load_graph

    await init_driver(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

    try:
        graph = await load_graph()

        case_dirs = sorted([
            d for d in FIXTURES_DIR.iterdir()
            if d.is_dir() and (d / "patient.json").exists()
        ])

        total = len(case_dirs)
        passed = 0
        failed = 0

        print(f"Running {total} statin fixtures...\n")

        for case_dir in case_dirs:
            case_name = case_dir.name
            patient = json.loads((case_dir / "patient.json").read_text())
            expected_outcome = json.loads((case_dir / "expected-outcome.json").read_text())
            expected_trace = json.loads((case_dir / "expected_trace.json").read_text())

            # Run evaluator
            trace = evaluate(patient, graph)

            # Determinism check: run again
            trace2 = evaluate(patient, graph)
            if _canonical_json(_strip_wall_clock(trace)) != _canonical_json(_strip_wall_clock(trace2)):
                print(f"FAIL  {case_name}")
                print("  Determinism failure: two runs differ")
                failed += 1
                continue

            # Check fixture
            failures = check_fixture(case_name, trace, expected_outcome, expected_trace)

            if failures:
                print(f"FAIL  {case_name}")
                for f in failures:
                    print(f)
                failed += 1
            else:
                print(f"PASS  {case_name}")
                passed += 1

        print(f"\n{passed}/{total} passed, {failed}/{total} failed")
        return 0 if failed == 0 else 1

    finally:
        await close_driver()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
