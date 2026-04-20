"""Report generation: emit markdown scorecard and JSON artifact from scorecard data.

Consumes the output of scorecard.build_scorecard() and writes:
  - scorecard.md — human-readable markdown report
  - scorecard.json — machine-readable JSON artifact
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.scorecard import DIMENSIONS, THESIS_MARGIN


def write_report(
    scorecard: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write scorecard.md and scorecard.json to the given directory.

    Returns (markdown_path, json_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "scorecard.md"
    json_path = output_dir / "scorecard.json"

    md_path.write_text(_render_markdown(scorecard))
    json_path.write_text(json.dumps(scorecard, indent=2) + "\n")

    return md_path, json_path


def write_readme(
    scorecard: dict[str, Any],
    output_dir: Path,
    commit_sha: str = "unknown",
    braintrust_url: str | None = None,
) -> Path:
    """Write README.md summarizing the thesis run."""
    readme_path = output_dir / "README.md"
    readme_path.write_text(_render_readme(scorecard, commit_sha, braintrust_url))
    return readme_path


def _render_markdown(scorecard: dict[str, Any]) -> str:
    """Render the scorecard as a markdown report."""
    lines: list[str] = []
    thesis = scorecard["thesis_gate"]
    consistency = scorecard["self_consistency"]

    # Header
    lines.append(f"# v1 Thesis Scorecard — {scorecard['run_name']}")
    lines.append("")
    lines.append(f"**Rubric version:** {scorecard['rubric_version']}")
    lines.append(f"**Judge runs:** {scorecard['n_runs']}")
    lines.append(f"**Fixtures:** {scorecard['n_fixtures']}")
    lines.append(f"**Arms:** {scorecard['n_arms']}")
    lines.append("")

    # Thesis gate verdict
    lines.append("## THESIS GATE: " + thesis["result"])
    lines.append("")
    if thesis["result"] == "PASS":
        lines.append(
            f"Arm C beats Arm B on multi-guideline fixtures by "
            f"**{thesis['margin']:.2f}** composite points "
            f"(required: ≥ {thesis['required_margin']:.1f})."
        )
    elif thesis["result"] == "FAIL":
        lines.append(
            f"Arm C margin over Arm B on multi-guideline fixtures: "
            f"**{thesis['margin']:.2f}** "
            f"(required: ≥ {thesis['required_margin']:.1f})."
        )
    else:
        lines.append(f"Reason: {thesis.get('reason', 'unknown')}")
    lines.append("")

    lines.append(f"- Arm B multi-guideline composite: **{thesis.get('arm_b_composite', 'N/A')}**")
    lines.append(f"- Arm C multi-guideline composite: **{thesis.get('arm_c_composite', 'N/A')}**")
    lines.append(f"- Margin (C - B): **{thesis.get('margin', 'N/A')}**")
    lines.append("")

    # Single-guideline comparison (informational)
    sg = thesis.get("single_guideline_comparison")
    if sg:
        lines.append("### Single-guideline comparison (informational)")
        lines.append("")
        lines.append(f"- Arm B: {sg['arm_b_composite']}")
        lines.append(f"- Arm C: {sg['arm_c_composite']}")
        lines.append(f"- Margin: {sg['margin']}")
        lines.append("")

    # Per-dimension gap on multi-guideline
    dim_gaps = thesis.get("dimension_gaps", {})
    if dim_gaps:
        lines.append("### Per-dimension gap (multi-guideline, C - B)")
        lines.append("")
        lines.append("| Dimension | Gap |")
        lines.append("|-----------|-----|")
        for dim in DIMENSIONS:
            gap = dim_gaps.get(dim, 0)
            lines.append(f"| {dim} | {gap:+.3f} |")
        lines.append("")

    # Self-consistency
    lines.append("## Self-consistency")
    lines.append("")
    if consistency["stable"]:
        lines.append(
            f"All arm/subset combinations have self-consistency SD ≤ "
            f"{consistency['threshold']}. Scores are stable."
        )
    else:
        lines.append("**WARNING: Rubric instability detected.**")
        lines.append("")
        for flag in consistency["flags"]:
            lines.append(f"- {flag['message']}")
    lines.append("")

    # Arm × subset summary table
    lines.append("## Summary by arm and subset")
    lines.append("")
    _render_summary_table(lines, scorecard["arm_subset_summary"])
    lines.append("")

    # Per-dimension breakdown
    lines.append("## Per-dimension breakdown")
    lines.append("")
    _render_dimension_table(lines, scorecard["arm_subset_summary"])
    lines.append("")

    # Per-fixture detail
    lines.append("## Per-fixture scores")
    lines.append("")
    _render_fixture_table(lines, scorecard["fixture_scores"])
    lines.append("")

    # Failure analysis
    failure = thesis.get("failure_analysis")
    if failure:
        lines.append("## Failure analysis")
        lines.append("")
        lines.append(f"**Classification:** {failure['classification']}")
        lines.append("")
        lines.append(failure["interpretation"])
        lines.append("")
        if failure["underperforming_dimensions"]:
            lines.append(
                "**Underperforming dimensions:** "
                + ", ".join(failure["underperforming_dimensions"])
            )
            lines.append("")
        lines.append("**Hypotheses:**")
        lines.append("")
        for h in failure["hypotheses"]:
            lines.append(f"- {h}")
        lines.append("")
        lines.append("**Recommended next features:**")
        lines.append("")
        for r in failure["recommended_next"]:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)


def _render_summary_table(
    lines: list[str],
    arm_subset: list[dict[str, Any]],
) -> None:
    """Render arm × subset summary as a markdown table."""
    lines.append(
        "| Arm | Subset | N | Composite | SD (fixtures) | SD (consistency) |"
    )
    lines.append("|-----|--------|---|-----------|---------------|-----------------|")
    for entry in arm_subset:
        lines.append(
            f"| {entry['arm'].upper()} "
            f"| {entry['subset']} "
            f"| {entry['n_fixtures']} "
            f"| {entry['composite_mean']:.3f} "
            f"| {entry['composite_fixture_sd']:.3f} "
            f"| {entry['composite_self_consistency_sd']:.3f} |"
        )


def _render_dimension_table(
    lines: list[str],
    arm_subset: list[dict[str, Any]],
) -> None:
    """Render per-dimension means by arm × subset."""
    header = "| Arm | Subset |"
    sep = "|-----|--------|"
    for dim in DIMENSIONS:
        short = dim[:15]
        header += f" {short} |"
        sep += f" {'---':>15} |"
    lines.append(header)
    lines.append(sep)

    for entry in arm_subset:
        row = f"| {entry['arm'].upper()} | {entry['subset']} |"
        for dim in DIMENSIONS:
            val = entry["dimensions"].get(dim, 0)
            row += f" {val:.3f} |"
        lines.append(row)


def _render_fixture_table(
    lines: list[str],
    fixture_scores: list[dict[str, Any]],
) -> None:
    """Render per-fixture scores as a markdown table."""
    lines.append("| Fixture | Arm | Subset | Composite | SD |")
    lines.append("|---------|-----|--------|-----------|-----|")
    for fs in fixture_scores:
        lines.append(
            f"| {fs['fixture']} "
            f"| {fs['arm'].upper()} "
            f"| {fs['subset']} "
            f"| {fs['composite_mean']:.3f} "
            f"| {fs['composite_sd']:.3f} |"
        )


def _render_readme(
    scorecard: dict[str, Any],
    commit_sha: str,
    braintrust_url: str | None,
) -> str:
    """Render the thesis run README."""
    thesis = scorecard["thesis_gate"]
    lines: list[str] = []

    lines.append("# v1 Thesis Run")
    lines.append("")
    lines.append(f"**Commit:** `{commit_sha}`")
    lines.append(f"**Date:** {scorecard.get('run_name', 'v1-thesis')}")
    lines.append(f"**Rubric:** {scorecard['rubric_version']}")
    lines.append(f"**Judge runs:** {scorecard['n_runs']} (self-consistency)")
    if braintrust_url:
        lines.append(f"**Braintrust experiment:** [{braintrust_url}]({braintrust_url})")
    lines.append("")

    # Result
    lines.append("## Result")
    lines.append("")
    lines.append(f"**THESIS GATE: {thesis['result']}**")
    lines.append("")

    if thesis["result"] == "PASS":
        lines.append(
            f"The graph-context arm (Arm C) outperforms flat RAG (Arm B) on "
            f"multi-guideline fixtures by {thesis['margin']:.2f} composite points "
            f"(threshold: ≥ {THESIS_MARGIN}). The convergence summary — surfacing "
            f"that multiple guidelines independently recommend the same therapeutic "
            f"actions via shared clinical entities — provides the LLM with structural "
            f"information that flat text retrieval cannot replicate."
        )
    elif thesis["result"] == "FAIL":
        failure = thesis.get("failure_analysis", {})
        lines.append(
            f"Arm C margin over Arm B: {thesis['margin']:.2f} (required: ≥ {THESIS_MARGIN})."
        )
        lines.append("")
        lines.append(f"**Classification:** {failure.get('classification', 'unknown')}")
        lines.append("")
        lines.append(failure.get("interpretation", ""))
    lines.append("")

    # Setup
    lines.append("## Setup")
    lines.append("")
    lines.append(f"- **Fixtures:** {scorecard['n_fixtures']} total (12 single-guideline, 4 multi-guideline)")
    lines.append("- **Arms:** A (vanilla LLM), B (flat RAG), C (graph context + convergence)")
    lines.append("- **Arm model:** claude-sonnet-4-6-20250514")
    lines.append("- **Judge model:** claude-opus-4-6-20250610")
    lines.append("- **Temperature:** 0 (all calls)")
    lines.append("- **Self-consistency:** 3 judge runs per fixture/arm")
    lines.append("")

    # Interpretation
    lines.append("## Interpretation")
    lines.append("")
    if thesis["result"] == "PASS":
        lines.append(
            "Convergence visibility is a genuine graph capability that flat RAG cannot "
            "replicate. When multiple guidelines independently point at the same medication "
            "node, the graph surfaces this structural agreement explicitly. The LLM anchors "
            "on this multi-source evidence to produce better-integrated recommendations."
        )
        lines.append("")
        lines.append(
            "This does not mean the graph's value is limited to convergence. When "
            "clinician-reviewed cross-guideline edges (PREEMPTED_BY, MODIFIES) return, "
            "a follow-up thesis run can measure the incremental value of edge-based "
            "conflict resolution on top of convergence."
        )
    else:
        lines.append("See failure analysis in `scorecard.md` for details and next steps.")

    lines.append("")

    # Files
    lines.append("## Files")
    lines.append("")
    lines.append("- `scorecard.md` — full scorecard with per-fixture breakdowns")
    lines.append("- `scorecard.json` — machine-readable scorecard")
    lines.append("- `README.md` — this file")
    lines.append("")

    return "\n".join(lines)
