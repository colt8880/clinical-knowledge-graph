"""Scorecard aggregation: per-arm totals with breakdowns by dimension and fixture subset.

Consumes results from Braintrust experiments (via fetch_from_braintrust())
or a list of run results, and produces a structured scorecard suitable for
report.py to render as markdown + JSON.

Fixture subsets:
  - single-guideline: statins, cholesterol, kdigo (12 fixtures)
  - multi-guideline: cross-domain (4 fixtures)

The thesis gate is evaluated against the multi-guideline subset only:
  Arm C mean composite > Arm B mean composite by >= 0.5 points.
"""

from __future__ import annotations

import math
from typing import Any

from harness.config import ARM_IDS, RUBRIC_VERSION


# Preregistered margin per ADR 0020
THESIS_MARGIN = 0.5

# Self-consistency SD threshold per ADR 0020
SELF_CONSISTENCY_SD_THRESHOLD = 0.3

# Multi-guideline guideline directory name
MULTI_GUIDELINE_DIR = "cross-domain"

DIMENSIONS = [
    "completeness",
    "clinical_appropriateness",
    "prioritization",
    "integration",
]


def classify_fixture(fixture_id: str) -> str:
    """Classify a fixture as 'single-guideline' or 'multi-guideline'.

    Fixture IDs look like 'statins/01-high-risk-55m-smoker' or 'cross-domain/case-01'.
    """
    guideline = fixture_id.split("/")[0]
    if guideline == MULTI_GUIDELINE_DIR:
        return "multi-guideline"
    return "single-guideline"


def _extract_dim_score(scores: dict[str, Any], dim: str) -> float:
    """Extract a numeric score from the rubric_scores dict."""
    rubric = scores.get("rubric_scores", scores.get("scores", {}))
    val = rubric.get(dim, {})
    if isinstance(val, dict):
        return float(val.get("score", 0))
    if isinstance(val, (int, float)):
        return float(val)
    return 0.0


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    """Sample standard deviation (Bessel's correction, N-1 denominator)."""
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    variance = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def build_scorecard(
    run_results: list[list[dict[str, Any]]],
    run_name: str = "v1-thesis",
) -> dict[str, Any]:
    """Build a scorecard from one or more harness runs (for self-consistency).

    Args:
        run_results: List of runs, where each run is a list of result dicts.
            Each result dict has: fixture, arm, composite, scores.
            scores contains rubric_scores with per-dimension scores.
        run_name: Name for this scorecard run.

    Returns:
        Structured scorecard dict suitable for report.py.
    """
    n_runs = len(run_results)

    # Collect per-fixture, per-arm scores across runs
    # Key: (fixture_id, arm_id) -> list of per-run score dicts
    fixture_arm_runs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    all_fixtures: set[str] = set()
    all_arms: set[str] = set()

    for run in run_results:
        for entry in run:
            fid = entry["fixture"]
            arm = entry["arm"]
            all_fixtures.add(fid)
            all_arms.add(arm)
            key = (fid, arm)
            if key not in fixture_arm_runs:
                fixture_arm_runs[key] = []
            fixture_arm_runs[key].append(entry)

    # Build per-fixture, per-arm aggregated scores (mean across runs)
    fixture_scores: list[dict[str, Any]] = []
    for fid in sorted(all_fixtures):
        subset = classify_fixture(fid)
        for arm in sorted(all_arms):
            key = (fid, arm)
            entries = fixture_arm_runs.get(key, [])
            if not entries:
                continue

            # Per-dimension: collect across runs, compute mean + SD
            dim_means: dict[str, float] = {}
            dim_sds: dict[str, float] = {}
            for dim in DIMENSIONS:
                values = [_extract_dim_score(e.get("scores", {}), dim) for e in entries]
                dim_means[dim] = round(_mean(values), 3)
                dim_sds[dim] = round(_stddev(values), 3)

            # Composite across runs
            composites = []
            for e in entries:
                rubric = e.get("scores", {}).get("rubric_scores", e.get("scores", {}).get("scores", {}))
                c = rubric.get("composite", 0)
                if isinstance(c, (int, float)):
                    composites.append(float(c))
                else:
                    composites.append(0.0)

            fixture_scores.append({
                "fixture": fid,
                "arm": arm,
                "subset": subset,
                "n_runs": len(entries),
                "dimensions": dim_means,
                "dimensions_sd": dim_sds,
                "composite_mean": round(_mean(composites), 3),
                "composite_sd": round(_stddev(composites), 3),
            })

    # Aggregate by arm × subset
    arm_subset_agg = _aggregate_by_arm_subset(fixture_scores)

    # Evaluate thesis gate
    thesis = _evaluate_thesis(arm_subset_agg)

    # Self-consistency flags
    consistency = _check_self_consistency(arm_subset_agg)

    return {
        "run_name": run_name,
        "rubric_version": RUBRIC_VERSION,
        "n_runs": n_runs,
        "n_fixtures": len(all_fixtures),
        "n_arms": len(all_arms),
        "fixture_scores": fixture_scores,
        "arm_subset_summary": arm_subset_agg,
        "thesis_gate": thesis,
        "self_consistency": consistency,
    }


def _aggregate_by_arm_subset(
    fixture_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate fixture scores by arm × subset."""
    # Group by (arm, subset)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for fs in fixture_scores:
        key = (fs["arm"], fs["subset"])
        if key not in groups:
            groups[key] = []
        groups[key].append(fs)

    result = []
    for (arm, subset), entries in sorted(groups.items()):
        dim_means: dict[str, float] = {}
        dim_sds: dict[str, float] = {}
        for dim in DIMENSIONS:
            values = [e["dimensions"][dim] for e in entries]
            dim_means[dim] = round(_mean(values), 3)
            # SD of fixture means (how much do fixtures vary within this arm/subset)
            dim_sds[dim] = round(_stddev(values), 3)

        composites = [e["composite_mean"] for e in entries]

        # Self-consistency: mean of per-fixture SDs
        consistency_sds = [e["composite_sd"] for e in entries]
        mean_consistency_sd = round(_mean(consistency_sds), 3)

        result.append({
            "arm": arm,
            "subset": subset,
            "n_fixtures": len(entries),
            "dimensions": dim_means,
            "dimensions_fixture_sd": dim_sds,
            "composite_mean": round(_mean(composites), 3),
            "composite_fixture_sd": round(_stddev(composites), 3),
            "composite_self_consistency_sd": mean_consistency_sd,
        })

    return result


def _evaluate_thesis(
    arm_subset_agg: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate the thesis gate: Arm C > Arm B by >= THESIS_MARGIN on multi-guideline."""
    arm_b_multi = None
    arm_c_multi = None
    arm_b_single = None
    arm_c_single = None

    for entry in arm_subset_agg:
        if entry["arm"] == "b" and entry["subset"] == "multi-guideline":
            arm_b_multi = entry
        elif entry["arm"] == "c" and entry["subset"] == "multi-guideline":
            arm_c_multi = entry
        elif entry["arm"] == "b" and entry["subset"] == "single-guideline":
            arm_b_single = entry
        elif entry["arm"] == "c" and entry["subset"] == "single-guideline":
            arm_c_single = entry

    if arm_b_multi is None or arm_c_multi is None:
        return {
            "result": "INCOMPLETE",
            "reason": "Missing Arm B or Arm C data for multi-guideline subset",
            "margin": None,
            "arm_b_composite": None,
            "arm_c_composite": None,
            "required_margin": THESIS_MARGIN,
        }

    b_comp = arm_b_multi["composite_mean"]
    c_comp = arm_c_multi["composite_mean"]
    margin = round(c_comp - b_comp, 3)

    passed = margin >= THESIS_MARGIN

    # Per-dimension gap on multi-guideline
    dim_gaps: dict[str, float] = {}
    for dim in DIMENSIONS:
        b_val = arm_b_multi["dimensions"].get(dim, 0)
        c_val = arm_c_multi["dimensions"].get(dim, 0)
        dim_gaps[dim] = round(c_val - b_val, 3)

    result: dict[str, Any] = {
        "result": "PASS" if passed else "FAIL",
        "margin": margin,
        "arm_b_composite": b_comp,
        "arm_c_composite": c_comp,
        "required_margin": THESIS_MARGIN,
        "dimension_gaps": dim_gaps,
    }

    # Single-guideline comparison (informational, not gating)
    if arm_b_single and arm_c_single:
        result["single_guideline_comparison"] = {
            "arm_b_composite": arm_b_single["composite_mean"],
            "arm_c_composite": arm_c_single["composite_mean"],
            "margin": round(
                arm_c_single["composite_mean"] - arm_b_single["composite_mean"], 3
            ),
        }

    if not passed:
        result["failure_analysis"] = _build_failure_analysis(
            margin, dim_gaps, arm_b_multi, arm_c_multi
        )

    return result


def _build_failure_analysis(
    margin: float,
    dim_gaps: dict[str, float],
    arm_b: dict[str, Any],
    arm_c: dict[str, Any],
) -> dict[str, Any]:
    """Build failure analysis when thesis gate fails."""
    # Identify underperforming dimensions
    underperforming = [
        dim for dim, gap in sorted(dim_gaps.items(), key=lambda x: x[1])
        if gap < THESIS_MARGIN / len(DIMENSIONS)
    ]

    # Classify the failure
    if margin >= 0.1:
        classification = "thesis_signal_below_threshold"
        interpretation = (
            f"Arm C leads by {margin:.2f} points — signal present but below "
            f"the {THESIS_MARGIN} threshold. Likely addressable via serialization improvements."
        )
    elif margin >= 0:
        classification = "marginal_or_tie"
        interpretation = (
            "Arm C does not meaningfully outperform Arm B. Either Arm B's RAG chunks "
            "contain convergence-relevant prose, or the convergence summary is not "
            "informative enough to move the needle."
        )
    else:
        classification = "arm_c_loss"
        interpretation = (
            "Arm B outperforms Arm C. Most likely cause: Arm B's RAG chunks happen "
            "to contain convergence-relevant prose (e.g., 'both USPSTF and ACC/AHA "
            "recommend...'), and the graph's structured representation adds overhead "
            "without enough compensating value."
        )

    hypotheses = []
    if "integration" in underperforming:
        hypotheses.append(
            "Serialization gap: convergence summary may not be surfacing "
            "the cross-guideline agreement clearly enough for the LLM."
        )
    if "completeness" in underperforming:
        hypotheses.append(
            "Retrieval gap: Arm B chunks may be more comprehensive than expected, "
            "covering actions the graph context misses."
        )
    if not underperforming:
        hypotheses.append(
            "Fixture construction gap: cross-domain cases may not exercise "
            "convergence strongly enough to differentiate the arms."
        )
    hypotheses.append(
        "Genuine null result: the graph's convergence visibility does not add "
        "enough value over flat RAG at this rubric granularity."
    )

    return {
        "classification": classification,
        "interpretation": interpretation,
        "underperforming_dimensions": underperforming,
        "hypotheses": hypotheses,
        "recommended_next": [
            "Improve convergence serialization (richer prose, explicit multi-source evidence table)",
            "Audit Arm B retrieval quality on multi-guideline fixtures",
            "Add more cross-domain fixtures with stronger convergence signal",
        ],
    }


def _check_self_consistency(
    arm_subset_agg: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check self-consistency across judge runs."""
    flags: list[dict[str, str]] = []
    all_ok = True

    for entry in arm_subset_agg:
        sd = entry["composite_self_consistency_sd"]
        if sd > SELF_CONSISTENCY_SD_THRESHOLD:
            all_ok = False
            flags.append({
                "arm": entry["arm"],
                "subset": entry["subset"],
                "sd": str(sd),
                "threshold": str(SELF_CONSISTENCY_SD_THRESHOLD),
                "message": (
                    f"Arm {entry['arm'].upper()} on {entry['subset']} has "
                    f"self-consistency SD {sd:.3f} > {SELF_CONSISTENCY_SD_THRESHOLD}. "
                    "Rubric instability detected."
                ),
            })

    return {
        "stable": all_ok,
        "threshold": SELF_CONSISTENCY_SD_THRESHOLD,
        "flags": flags,
    }


def _denormalize_score(val: float) -> float:
    """Convert a Braintrust 0-1 score back to 1-5 rubric scale."""
    return (val * 4) + 1


def fetch_from_braintrust(
    run_name: str,
    verbose: bool = False,
) -> list[list[dict[str, Any]]]:
    """Fetch results from Braintrust experiments and convert to run_results format.

    Looks for experiments named '{run_name}-arm-{a,b,c}'. Each experiment
    may have multiple trials (from trial_count). Returns one run_results list
    per trial.

    Note: init_experiment(open=True) may return rows from prior experiment
    versions with the same name. Rows without scores (stale or errored) are
    dropped. Use verbose=True to see fetch diagnostics.
    """
    import braintrust

    all_entries: list[dict[str, Any]] = []

    for arm_id in ARM_IDS:
        experiment_name = f"{run_name}-arm-{arm_id}"
        try:
            experiment = braintrust.init_experiment(
                "clinical-knowledge-graph",
                experiment=experiment_name,
                open=True,
            )
        except Exception as e:
            print(f"Warning: could not load experiment '{experiment_name}': {e}")
            continue

        total_rows = 0
        scored_rows = 0
        dropped_no_scores = 0
        dropped_no_fixture = 0

        for row in experiment.fetch():
            total_rows += 1
            # fixture_id may be in top-level metadata or nested in input.metadata
            fixture_id = (row.get("metadata") or {}).get("fixture_id", "")
            if not fixture_id:
                inp = row.get("input") or {}
                fixture_id = (inp.get("metadata") or {}).get("fixture_id", "")
            scores = row.get("scores") or {}
            if not scores:
                dropped_no_scores += 1
                continue  # Skip rows with no scores (stale versions or errors)
            if not fixture_id:
                dropped_no_fixture += 1
                continue

            scored_rows += 1

            # Denormalize from 0-1 back to 1-5
            rubric_scores: dict[str, Any] = {}
            for dim in DIMENSIONS:
                raw = scores.get(dim, 0)
                rubric_scores[dim] = {"score": _denormalize_score(raw), "rationale": ""}
            composite_raw = scores.get("composite", 0)
            rubric_scores["composite"] = _denormalize_score(composite_raw)

            all_entries.append({
                "fixture": fixture_id,
                "arm": arm_id,
                "composite": rubric_scores["composite"],
                "scores": {"rubric_scores": rubric_scores},
            })

        if verbose:
            print(
                f"[fetch] {experiment_name}: "
                f"{total_rows} total, {scored_rows} scored, "
                f"{dropped_no_scores} dropped (no scores), "
                f"{dropped_no_fixture} dropped (no fixture_id)"
            )

    if not all_entries:
        return []

    # For now, return as a single run (Braintrust averages trials internally)
    return [all_entries]
