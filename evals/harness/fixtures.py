"""Fixture discovery and loading utilities.

Shared by the eval runner and tests. Walks evals/fixtures/ to find
fixture directories containing patient context and expected actions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from harness.config import FIXTURES_ROOT

# Multi-guideline guideline directory name
MULTI_GUIDELINE_DIR = "cross-domain"


def _patient_file(case_dir: Path) -> Path | None:
    """Return the patient context file path, accepting either naming convention."""
    for name in ("patient.json", "patient-context.json"):
        p = case_dir / name
        if p.exists():
            return p
    return None


def discover_fixtures(fixture_filter: str | None = None) -> list[Path]:
    """Discover fixture directories under evals/fixtures/.

    If fixture_filter is set (e.g., "statins/01-high-risk-55m-smoker"),
    return only that fixture. If it starts with "_guideline:", return all
    fixtures for that guideline directory. Otherwise return all fixtures
    that have a patient file and expected-actions.json.
    """
    if fixture_filter and fixture_filter.startswith("_guideline:"):
        guideline_name = fixture_filter.split(":", 1)[1]
        guideline_dir = FIXTURES_ROOT / guideline_name
        if not guideline_dir.exists() or not guideline_dir.is_dir():
            print(f"Guideline fixture directory not found: {guideline_name}", file=sys.stderr)
            sys.exit(1)
        fixtures: list[Path] = []
        for case_dir in sorted(guideline_dir.iterdir()):
            if not case_dir.is_dir():
                continue
            if _patient_file(case_dir) and (case_dir / "expected-actions.json").exists():
                fixtures.append(case_dir)
        return fixtures

    if fixture_filter:
        fixture_dir = FIXTURES_ROOT / fixture_filter
        if not fixture_dir.exists():
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

    fixtures = []
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
            if _patient_file(case_dir) and (case_dir / "expected-actions.json").exists():
                fixtures.append(case_dir)
    return fixtures


def load_fixture(fixture_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load patient context and expected actions from a fixture directory."""
    pf = _patient_file(fixture_dir)
    if pf is None:
        raise FileNotFoundError(f"No patient file in {fixture_dir}")
    patient = json.loads(pf.read_text())
    expected = json.loads((fixture_dir / "expected-actions.json").read_text())
    return patient, expected


def fixture_id(fixture_dir: Path) -> str:
    """Return a human-readable fixture ID like 'statins/01-high-risk-55m-smoker'."""
    return f"{fixture_dir.parent.name}/{fixture_dir.name}"


def classify_fixture(fid: str) -> str:
    """Classify a fixture as 'single-guideline' or 'multi-guideline'."""
    guideline = fid.split("/")[0]
    if guideline == MULTI_GUIDELINE_DIR:
        return "multi-guideline"
    return "single-guideline"


def load_dataset(
    fixture_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Load fixtures into the shape Braintrust Eval() expects.

    Returns a list of dicts with input, expected, and metadata keys.
    """
    fixtures = discover_fixtures(fixture_filter)
    dataset = []
    for fix_dir in fixtures:
        fid = fixture_id(fix_dir)
        patient_context, expected_actions = load_fixture(fix_dir)
        dataset.append({
            "input": patient_context,
            "expected": expected_actions,
            "metadata": {
                "fixture_id": fid,
                "guideline": fix_dir.parent.name,
                "subset": classify_fixture(fid),
            },
        })
    return dataset
