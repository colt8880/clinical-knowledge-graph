"""Braintrust integration: logs datasets, experiments, and scores.

Optional at runtime: if BRAINTRUST_API_KEY is unset, all methods are
no-ops and the harness logs results locally to evals/results/<timestamp>/.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.config import RESULTS_ROOT, RUBRIC_VERSION


def _is_enabled() -> bool:
    """Check if Braintrust integration is enabled (API key present)."""
    return bool(os.environ.get("BRAINTRUST_API_KEY"))


def _ensure_results_dir(timestamp: str) -> Path:
    """Create and return a timestamped results directory for local fallback."""
    results_dir = RESULTS_ROOT / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


class BraintrustLogger:
    """Logs eval results to Braintrust or local fallback.

    Usage:
        logger = BraintrustLogger()
        logger.start_experiment("statins-baseline")
        logger.log_entry(fixture_id, arm_id, output, scores)
        logger.finish_experiment()
    """

    def __init__(self, timestamp: str | None = None) -> None:
        self._enabled = _is_enabled()
        self._experiment = None
        self._experiment_name: str | None = None
        self._timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self._local_entries: list[dict[str, Any]] = []

        if self._enabled:
            try:
                import braintrust
                self._bt = braintrust
            except ImportError:
                print("Warning: braintrust package not installed. Falling back to local logging.")
                self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def start_experiment(self, name: str) -> None:
        """Start a new Braintrust experiment or prepare local logging."""
        self._experiment_name = name
        self._local_entries = []

        if self._enabled:
            self._experiment = self._bt.init(
                project="clinical-knowledge-graph",
                experiment=f"{name}-{self._timestamp}",
            )

    def log_entry(
        self,
        fixture_id: str,
        arm_id: str,
        patient_context: dict[str, Any],
        output: dict[str, Any],
        scores: dict[str, Any],
        expected_actions: dict[str, Any],
    ) -> None:
        """Log a single fixture × arm result."""
        rubric_scores = scores.get("rubric_scores", {})
        structural = scores.get("structural_checks", {})

        entry = {
            "fixture_id": fixture_id,
            "arm_id": arm_id,
            "rubric_version": RUBRIC_VERSION,
            "scores": {
                "completeness": _extract_score(rubric_scores, "completeness"),
                "clinical_appropriateness": _extract_score(rubric_scores, "clinical_appropriateness"),
                "prioritization": _extract_score(rubric_scores, "prioritization"),
                "integration": _extract_score(rubric_scores, "integration"),
                "composite": rubric_scores.get("composite", 0),
            },
            "structural_checks": structural,
            "model": output.get("model"),
            "usage": output.get("usage"),
        }

        self._local_entries.append(entry)

        if self._enabled and self._experiment is not None:
            # Braintrust requires scores in [0, 1]; our rubric is 1-5.
            # Normalize: (score - 1) / 4 maps 1→0, 5→1.
            def _norm(val: float) -> float:
                return max(0.0, min(1.0, (val - 1) / 4))

            self._experiment.log(
                input={"patient_context": patient_context, "fixture_id": fixture_id},
                output=output.get("parsed", {}),
                expected=expected_actions,
                scores={
                    "completeness": _norm(_extract_score(rubric_scores, "completeness")),
                    "clinical_appropriateness": _norm(_extract_score(rubric_scores, "clinical_appropriateness")),
                    "prioritization": _norm(_extract_score(rubric_scores, "prioritization")),
                    "integration": _norm(_extract_score(rubric_scores, "integration")),
                    "composite": _norm(rubric_scores.get("composite", 0)),
                },
                metadata={
                    "arm_id": arm_id,
                    "fixture_id": fixture_id,
                    "rubric_version": RUBRIC_VERSION,
                },
            )

    def finish_experiment(self) -> Path | None:
        """Finalize the experiment. Returns the local results path (always written)."""
        # Always write local results
        results_dir = _ensure_results_dir(self._timestamp)
        results_file = results_dir / "results.json"

        summary = self._build_summary()
        results_data = {
            "experiment": self._experiment_name,
            "timestamp": self._timestamp,
            "rubric_version": RUBRIC_VERSION,
            "entries": self._local_entries,
            "summary": summary,
        }

        results_file.write_text(json.dumps(results_data, indent=2) + "\n")

        # Write scorecard
        scorecard_file = results_dir / "scorecard.txt"
        scorecard_file.write_text(self._format_scorecard(summary))

        if self._enabled and self._experiment is not None:
            self._experiment.flush()

        return results_dir

    def _build_summary(self) -> dict[str, Any]:
        """Build aggregate summary statistics per arm."""
        arms: dict[str, list[dict[str, Any]]] = {}
        for entry in self._local_entries:
            arm_id = entry["arm_id"]
            if arm_id not in arms:
                arms[arm_id] = []
            arms[arm_id].append(entry)

        summary: dict[str, Any] = {}
        for arm_id, entries in sorted(arms.items()):
            scores_by_dim: dict[str, list[float]] = {
                "completeness": [],
                "clinical_appropriateness": [],
                "prioritization": [],
                "integration": [],
                "composite": [],
            }
            for entry in entries:
                for dim, values in scores_by_dim.items():
                    values.append(entry["scores"].get(dim, 0))

            summary[arm_id] = {
                "n": len(entries),
                "mean_scores": {
                    dim: round(sum(values) / len(values), 2) if values else 0
                    for dim, values in scores_by_dim.items()
                },
            }

        return summary

    def _format_scorecard(self, summary: dict[str, Any]) -> str:
        """Format a human-readable scorecard."""
        lines: list[str] = [
            f"Eval Scorecard — {self._experiment_name}",
            f"Rubric: {RUBRIC_VERSION}  |  Timestamp: {self._timestamp}",
            "=" * 72,
            "",
        ]

        dims = ["completeness", "clinical_appropriateness", "prioritization", "integration", "composite"]
        header = f"{'Arm':<6}" + "".join(f"{d[:12]:>14}" for d in dims)
        lines.append(header)
        lines.append("-" * len(header))

        for arm_id, data in sorted(summary.items()):
            row = f"{'Arm ' + arm_id.upper():<6}"
            for dim in dims:
                val = data["mean_scores"].get(dim, 0)
                row += f"{val:>14.2f}"
            lines.append(row)

        lines.append("")
        lines.append(f"Fixtures per arm: {next(iter(summary.values()), {}).get('n', 0)}")
        lines.append("")

        return "\n".join(lines)


def _extract_score(rubric_scores: dict[str, Any], dimension: str) -> float:
    """Extract a numeric score from the rubric scores dict."""
    val = rubric_scores.get(dimension, {})
    if isinstance(val, dict):
        return val.get("score", 0)
    if isinstance(val, (int, float)):
        return val
    return 0
