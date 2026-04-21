#!/usr/bin/env python3
"""Discover cross-guideline interaction candidates by analyzing eligibility overlap.

Parses Recommendation nodes from seed files (--from-seeds) or a live Neo4j
instance (--from-graph), computes pairwise eligibility overlap for recs from
different guidelines, and generates docs/review/interaction-candidates.md.

Usage:
    python scripts/discover-interactions.py --from-seeds
    python scripts/discover-interactions.py --from-seeds --guidelines statins,cholesterol
    python scripts/discover-interactions.py --from-graph

The tool does mechanical overlap analysis. The clinician decides whether an
overlapping pair is preemption, modification, or no interaction.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Add scripts dir to path for predicate_parser import
sys.path.insert(0, str(Path(__file__).parent))

from predicate_parser import (
    EligibilityCriteria,
    eligibility_to_plain_english,
    parse_eligibility,
    _comparator_symbol,
    _display_code,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = REPO_ROOT / "graph" / "seeds"
OUTPUT_DIR = REPO_ROOT / "docs" / "review"

# Map seed file basenames to guideline IDs
SEED_FILE_GUIDELINE_MAP = {
    "statins.cypher": "guideline:uspstf-statin-2022",
    "cholesterol.cypher": "guideline:acc-aha-cholesterol-2018",
    "kdigo-ckd.cypher": "guideline:kdigo-ckd-2024",
}

# Friendly guideline display names
GUIDELINE_DISPLAY = {
    "guideline:uspstf-statin-2022": "USPSTF 2022 Statin Primary Prevention",
    "guideline:acc-aha-cholesterol-2018": "ACC/AHA 2018 Blood Cholesterol Management",
    "guideline:kdigo-ckd-2024": "KDIGO 2024 Chronic Kidney Disease",
}

# --guidelines flag values map to seed filenames
GUIDELINE_FLAG_MAP = {
    "statins": "statins.cypher",
    "cholesterol": "cholesterol.cypher",
    "kdigo": "kdigo-ckd.cypher",
}


@dataclass
class RecInfo:
    """Parsed recommendation metadata from a seed file."""

    id: str
    title: str
    evidence_grade: str
    intent: str
    guideline_id: str
    source_section: str
    structured_eligibility_raw: str
    eligibility: EligibilityCriteria | None = None
    strategy_ids: list[str] = field(default_factory=list)
    action_entity_ids: list[str] = field(default_factory=list)


@dataclass
class OverlapAnalysis:
    """Result of comparing two Recs' eligibility criteria."""

    age_overlap: str
    age_overlaps: bool
    condition_compatible: bool
    condition_notes: str
    shared_therapeutic_targets: list[str]
    candidate_type: str  # convergence / modification / no_interaction / manual_review
    notes: list[str] = field(default_factory=list)


def parse_recs_from_seeds(
    guideline_filter: set[str] | None = None,
) -> list[RecInfo]:
    """Parse Recommendation nodes and their strategies from .cypher seed files."""
    recs: list[RecInfo] = []
    strategy_actions: dict[str, list[str]] = {}  # strategy_id -> [entity_ids]
    rec_strategies: dict[str, list[str]] = {}  # rec_id -> [strategy_ids]

    seed_files = _get_seed_files(guideline_filter)

    for seed_file in seed_files:
        guideline_id = SEED_FILE_GUIDELINE_MAP.get(seed_file.name, "unknown")
        text = seed_file.read_text()

        # Extract Recommendation nodes
        for match in re.finditer(
            r"MERGE\s*\(\w+:Recommendation[:\w]*\s*\{id:\s*'([^']+)'\}\)"
            r".*?ON CREATE SET(.*?)(?=\n\n|\nMERGE|\nMATCH|$)",
            text,
            re.DOTALL,
        ):
            rec_id = match.group(1)
            props_block = match.group(2)

            title = _extract_prop(props_block, "title") or rec_id
            grade = _extract_prop(props_block, "evidence_grade") or ""
            intent = _extract_prop(props_block, "intent") or ""
            section = _extract_prop(props_block, "source_section") or ""
            elig_raw = _extract_prop(props_block, "structured_eligibility") or "{}"

            rec = RecInfo(
                id=rec_id,
                title=title,
                evidence_grade=grade,
                intent=intent,
                guideline_id=guideline_id,
                source_section=section,
                structured_eligibility_raw=elig_raw,
            )
            try:
                rec.eligibility = parse_eligibility(elig_raw)
            except (json.JSONDecodeError, Exception) as e:
                rec.eligibility = EligibilityCriteria(
                    manual_review_notes=[f"Parse error: {e}"]
                )
            recs.append(rec)

        # Extract OFFERS_STRATEGY edges: rec -> strategy
        for match in re.finditer(
            r"MATCH\s*\(\w+:Recommendation\s*\{id:\s*'([^']+)'\}\)\s*,"
            r"\s*\(\w+:Strategy\s*\{id:\s*'([^']+)'\}\)\s*\n"
            r"\s*MERGE\s*\(\w+\)-\[",
            text,
        ):
            rec_id = match.group(1)
            strat_id = match.group(2)
            rec_strategies.setdefault(rec_id, []).append(strat_id)

        # Extract INCLUDES_ACTION edges: strategy -> entity
        for match in re.finditer(
            r"MATCH\s*\(\w+:Strategy\s*\{id:\s*'([^']+)'\}\)\s*,"
            r"\s*\(\w+:(?:Medication|Observation|Procedure)\s*\{id:\s*'([^']+)'\}\)",
            text,
        ):
            strat_id = match.group(1)
            entity_id = match.group(2)
            strategy_actions.setdefault(strat_id, []).append(entity_id)

    # Also parse clinical-entities.cypher for strategies that reference entities
    # (already captured above since we parse all seed files)

    # Wire strategy actions back to recs
    for rec in recs:
        rec.strategy_ids = rec_strategies.get(rec.id, [])
        for strat_id in rec.strategy_ids:
            for entity_id in strategy_actions.get(strat_id, []):
                if entity_id not in rec.action_entity_ids:
                    rec.action_entity_ids.append(entity_id)

    return recs


def parse_recs_from_graph() -> list[RecInfo]:
    """Parse Recommendation nodes from a running Neo4j instance."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Error: neo4j driver not installed. Use --from-seeds or pip install neo4j.", file=sys.stderr)
        sys.exit(1)

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password123")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    recs: list[RecInfo] = []

    with driver.session() as session:
        # Get all Recs with their guideline
        result = session.run("""
            MATCH (r:Recommendation)-[:FROM_GUIDELINE]->(g:Guideline)
            RETURN r.id AS id, r.title AS title, r.evidence_grade AS grade,
                   r.intent AS intent, g.id AS guideline_id,
                   r.source_section AS section,
                   r.structured_eligibility AS eligibility
        """)
        for record in result:
            elig_raw = record["eligibility"] or "{}"
            rec = RecInfo(
                id=record["id"],
                title=record["title"] or record["id"],
                evidence_grade=record["grade"] or "",
                intent=record["intent"] or "",
                guideline_id=record["guideline_id"],
                source_section=record["section"] or "",
                structured_eligibility_raw=elig_raw,
            )
            try:
                rec.eligibility = parse_eligibility(elig_raw)
            except Exception as e:
                rec.eligibility = EligibilityCriteria(
                    manual_review_notes=[f"Parse error: {e}"]
                )
            recs.append(rec)

        # Get strategy → entity mappings
        result = session.run("""
            MATCH (r:Recommendation)-[:OFFERS_STRATEGY]->(s:Strategy)-[:INCLUDES_ACTION]->(e)
            WHERE e:Medication OR e:Observation OR e:Procedure
            RETURN r.id AS rec_id, s.id AS strat_id, e.id AS entity_id
        """)
        rec_entities: dict[str, list[str]] = {}
        rec_strats: dict[str, list[str]] = {}
        for record in result:
            rec_id = record["rec_id"]
            rec_entities.setdefault(rec_id, []).append(record["entity_id"])
            if record["strat_id"] not in rec_strats.setdefault(rec_id, []):
                rec_strats[rec_id].append(record["strat_id"])

        for rec in recs:
            rec.strategy_ids = rec_strats.get(rec.id, [])
            rec.action_entity_ids = list(set(rec_entities.get(rec.id, [])))

    driver.close()
    return recs


def compute_overlap(rec_a: RecInfo, rec_b: RecInfo) -> OverlapAnalysis:
    """Compute eligibility overlap between two Recs."""
    ea = rec_a.eligibility or EligibilityCriteria()
    eb = rec_b.eligibility or EligibilityCriteria()
    notes: list[str] = []

    # 1. Age range intersection
    a_min = ea.effective_age_min
    a_max = ea.effective_age_max
    b_min = eb.effective_age_min
    b_max = eb.effective_age_max

    age_overlaps = True
    if a_min is not None and b_max is not None and a_min > b_max:
        age_overlaps = False
    elif b_min is not None and a_max is not None and b_min > a_max:
        age_overlaps = False

    if age_overlaps:
        lo = max(a_min or 0, b_min or 0)
        hi = min(a_max or 999, b_max or 999)
        if hi >= 999:
            age_overlap_str = f"≥{lo}" if lo > 0 else "any age"
        else:
            age_overlap_str = f"{lo}–{hi}"
    else:
        age_overlap_str = (
            f"NO OVERLAP ({ea.age_range_str()} vs {eb.age_range_str()})"
        )

    # 2. Condition compatibility
    condition_compatible = True
    condition_notes_parts: list[str] = []

    # Conjunctive conditions: patient MUST have these
    a_req = set(ea.required_conditions)
    a_exc = set(ea.excluded_conditions)
    b_req = set(eb.required_conditions)
    b_exc = set(eb.excluded_conditions)

    # Check conjunctive conflicts: A requires what B excludes
    conflict_ab = a_req & b_exc
    conflict_ba = b_req & a_exc

    if conflict_ab:
        condition_compatible = False
        names = ", ".join(_display_code(c) for c in sorted(conflict_ab))
        condition_notes_parts.append(
            f"Rec A requires {names} which Rec B excludes"
        )
    if conflict_ba:
        condition_compatible = False
        names = ", ".join(_display_code(c) for c in sorted(conflict_ba))
        condition_notes_parts.append(
            f"Rec B requires {names} which Rec A excludes"
        )

    # Check disjunctive groups: if ALL branches of a disjunctive group
    # are excluded by the other Rec, there's no way to satisfy both.
    # A group is only fully excluded when it has ONLY condition branches
    # and all of them are excluded. Observation/medication branches
    # provide alternative paths that condition exclusions don't block.
    for group in ea.disjunctive_groups:
        has_non_condition_branches = bool(
            group.observations or group.medications or group.smoking_values
        )
        if (
            group.conditions
            and not has_non_condition_branches
            and all(c in b_exc for c in group.conditions)
        ):
            condition_compatible = False
            names = ", ".join(_display_code(c) for c in group.conditions)
            condition_notes_parts.append(
                f"All branches of Rec A disjunction ({names}) excluded by Rec B"
            )
    for group in eb.disjunctive_groups:
        has_non_condition_branches = bool(
            group.observations or group.medications or group.smoking_values
        )
        if (
            group.conditions
            and not has_non_condition_branches
            and all(c in a_exc for c in group.conditions)
        ):
            condition_compatible = False
            names = ", ".join(_display_code(c) for c in group.conditions)
            condition_notes_parts.append(
                f"All branches of Rec B disjunction ({names}) excluded by Rec A"
            )

    # Shared required conditions (conjunctive)
    shared_req = a_req & b_req
    if shared_req:
        names = ", ".join(_display_code(c) for c in sorted(shared_req))
        condition_notes_parts.append(f"Both require: {names}")

    # Shared conditions across disjunctive groups
    a_disj_conds = set()
    for group in ea.disjunctive_groups:
        a_disj_conds.update(group.conditions)
    b_disj_conds = set()
    for group in eb.disjunctive_groups:
        b_disj_conds.update(group.conditions)

    shared_disj = (a_disj_conds | a_req) & (b_disj_conds | b_req) - shared_req
    if shared_disj:
        names = ", ".join(_display_code(c) for c in sorted(shared_disj))
        condition_notes_parts.append(f"Shared condition (some disjunctive): {names}")

    condition_notes_str = "; ".join(condition_notes_parts) if condition_notes_parts else "Compatible"

    # 3. Shared therapeutic targets
    shared_entities = sorted(
        set(rec_a.action_entity_ids) & set(rec_b.action_entity_ids)
    )

    # 4. Classify candidate type
    if not age_overlaps or not condition_compatible:
        candidate_type = "no_interaction"
        notes.append("No eligibility overlap — cannot co-match the same patient")
    elif shared_entities:
        candidate_type = "convergence"
        notes.append(
            "Both recs' strategies target shared entities — "
            "potential PREEMPTED_BY (more specific preempts less specific) "
            "or reinforcing convergence"
        )
    else:
        candidate_type = "modification"
        notes.append(
            "Recs can co-match but target different therapeutic actions — "
            "potential MODIFIES (one adjusts the other's approach)"
        )

    # Flag manual review items
    if ea.manual_review_notes or eb.manual_review_notes:
        all_notes = ea.manual_review_notes + eb.manual_review_notes
        notes.append(f"⚠ Manual review needed: {'; '.join(all_notes)}")

    return OverlapAnalysis(
        age_overlap=age_overlap_str,
        age_overlaps=age_overlaps,
        condition_compatible=condition_compatible,
        condition_notes=condition_notes_str,
        shared_therapeutic_targets=shared_entities,
        candidate_type=candidate_type,
        notes=notes,
    )


def generate_review_document(
    recs: list[RecInfo],
    output_path: Path,
) -> list[tuple[RecInfo, RecInfo, OverlapAnalysis]]:
    """Generate the interaction-candidates.md review document."""
    # Build cross-guideline pairs
    pairs: list[tuple[RecInfo, RecInfo, OverlapAnalysis]] = []

    for i, rec_a in enumerate(recs):
        for rec_b in recs[i + 1 :]:
            if rec_a.guideline_id == rec_b.guideline_id:
                continue
            overlap = compute_overlap(rec_a, rec_b)
            pairs.append((rec_a, rec_b, overlap))

    # Group by candidate type
    convergence = [(a, b, o) for a, b, o in pairs if o.candidate_type == "convergence"]
    modification = [(a, b, o) for a, b, o in pairs if o.candidate_type == "modification"]
    no_interaction = [(a, b, o) for a, b, o in pairs if o.candidate_type == "no_interaction"]

    # Sort each group by guideline pair, then rec ID
    sort_key = lambda p: (p[0].guideline_id, p[1].guideline_id, p[0].id, p[1].id)
    convergence.sort(key=sort_key)
    modification.sort(key=sort_key)
    no_interaction.sort(key=sort_key)

    # Generate markdown
    lines: list[str] = []
    lines.append("# Cross-guideline interaction candidates")
    lines.append("")
    lines.append(
        f"Generated by `scripts/discover-interactions.py --from-seeds` on "
        f"{_today()}. See `docs/review/README.md` for reviewer instructions."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Convergence (shared therapeutic targets) | {len(convergence)} |")
    lines.append(f"| Modification candidates (different actions, same patient) | {len(modification)} |")
    lines.append(f"| No interaction (eligibility doesn't overlap) | {len(no_interaction)} |")
    lines.append(f"| **Total** | **{len(pairs)}** |")
    lines.append("")

    # --- Convergence section ---
    if convergence:
        lines.append("---")
        lines.append("")
        lines.append("# Convergence candidates")
        lines.append("")
        lines.append(
            "Both recs recommend the same medication(s) or action(s). "
            "Likely outcome: one **preempts** the other (the more specific or "
            "higher-authority rec wins), or this is **reinforcing convergence** "
            "already handled by the shared entity layer (no edge needed)."
        )
        lines.append("")
        for idx, (rec_a, rec_b, overlap) in enumerate(convergence, 1):
            _render_pair(lines, f"C{idx}", rec_a, rec_b, overlap)

    # --- Modification section ---
    if modification:
        lines.append("---")
        lines.append("")
        lines.append("# Modification candidates")
        lines.append("")
        lines.append(
            "Both recs can fire for the same patient but target different "
            "therapeutic actions. Likely outcome: one **modifies** the other "
            "(adjusts intensity, adds monitoring, flags a contraindication), "
            "or they are **unrelated** (different clinical domains, no interaction)."
        )
        lines.append("")
        for idx, (rec_a, rec_b, overlap) in enumerate(modification, 1):
            _render_pair(lines, f"M{idx}", rec_a, rec_b, overlap)

    # --- No interaction section ---
    if no_interaction:
        lines.append("---")
        lines.append("")
        lines.append("# No interaction (obvious rejects)")
        lines.append("")
        lines.append(
            "These pairs cannot co-match the same patient — age ranges don't "
            "overlap, or one rec requires a condition the other excludes. "
            "Listed for completeness. Expected verdict: **reject**."
        )
        lines.append("")
        for idx, (rec_a, rec_b, overlap) in enumerate(no_interaction, 1):
            _render_pair(lines, f"X{idx}", rec_a, rec_b, overlap)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return pairs


def _render_pair(
    lines: list[str],
    label: str,
    rec_a: RecInfo,
    rec_b: RecInfo,
    overlap: OverlapAnalysis,
) -> None:
    """Render a single pair in the new side-by-side format."""
    ea = rec_a.eligibility or EligibilityCriteria()
    eb = rec_b.eligibility or EligibilityCriteria()

    g_a = _short_guideline(rec_a.guideline_id)
    g_b = _short_guideline(rec_b.guideline_id)

    lines.append(f"## {label}: {rec_a.title} ↔ {rec_b.title}")
    lines.append("")

    # Clinical scenario
    scenario = _build_clinical_scenario(rec_a, rec_b, ea, eb, overlap)
    lines.append(f"> **Clinical scenario:** {scenario}")
    lines.append("")

    # Side-by-side comparison table
    lines.append("| | Rec A | Rec B |")
    lines.append("|---|---|---|")
    lines.append(f"| **Guideline** | {g_a} | {g_b} |")
    lines.append(f"| **ID** | `{rec_a.id}` | `{rec_b.id}` |")
    lines.append(f"| **Grade** | {rec_a.evidence_grade} | {rec_b.evidence_grade} |")
    lines.append(f"| **Intent** | {rec_a.intent} | {rec_b.intent} |")
    lines.append(f"| **Age** | {ea.age_range_str()} | {eb.age_range_str()} |")

    # Eligibility rows — break out the key criteria
    a_requires = _eligibility_requires(ea)
    b_requires = _eligibility_requires(eb)
    a_excludes = _eligibility_excludes(ea)
    b_excludes = _eligibility_excludes(eb)

    lines.append(f"| **Requires** | {a_requires} | {b_requires} |")
    lines.append(f"| **Excludes** | {a_excludes} | {b_excludes} |")

    # Action targets
    a_actions = ", ".join(_display_code(e) for e in sorted(rec_a.action_entity_ids)) or "—"
    b_actions = ", ".join(_display_code(e) for e in sorted(rec_b.action_entity_ids)) or "—"
    lines.append(f"| **Actions** | {a_actions} | {b_actions} |")
    lines.append("")

    # Overlap summary (compact)
    lines.append(f"**Age overlap:** {overlap.age_overlap}")
    if overlap.condition_notes != "Compatible":
        lines.append(f" · **Conditions:** {overlap.condition_notes}")
    if overlap.shared_therapeutic_targets:
        targets = ", ".join(_display_code(t) for t in overlap.shared_therapeutic_targets)
        lines.append(f" · **Shared targets:** {targets}")
    lines.append("")

    # Pre-populated verdict
    _render_verdict(lines, rec_a, rec_b, overlap, g_a, g_b)

    lines.append("---")
    lines.append("")


def _build_clinical_scenario(
    rec_a: RecInfo,
    rec_b: RecInfo,
    ea: EligibilityCriteria,
    eb: EligibilityCriteria,
    overlap: OverlapAnalysis,
) -> str:
    """Build a plain-English sentence describing the specific patient who triggers both recs.

    The scenario must reflect the INTERSECTION of both recs' requirements AND
    the UNION of both recs' exclusions — the narrowest population where both fire.
    """
    if not overlap.age_overlaps or not overlap.condition_compatible:
        reasons: list[str] = []
        if not overlap.age_overlaps:
            reasons.append("age ranges do not overlap")
        if not overlap.condition_compatible:
            reasons.append("mutually exclusive conditions")
        return f"No patient can trigger both — {' and '.join(reasons)}."

    # --- Build the positive requirements (intersection) ---

    # Age overlap range
    a_lo = ea.effective_age_min or 0
    a_hi = ea.effective_age_max or 999
    b_lo = eb.effective_age_min or 0
    b_hi = eb.effective_age_max or 999
    overlap_lo = max(a_lo, b_lo)
    overlap_hi = min(a_hi, b_hi)
    mid_age = (overlap_lo + overlap_hi) // 2

    # Collect ALL positive requirements from both recs (deduplicated)
    req_parts: list[str] = []
    seen: set[str] = set()

    def _add_req(text: str) -> None:
        if text not in seen:
            seen.add(text)
            req_parts.append(text)

    # Conjunctive conditions from both recs
    for c in ea.required_conditions + eb.required_conditions:
        _add_req(_display_code(c))

    # Disjunctive groups — pick one satisfying branch per group
    # Label which rec the requirement comes from when it's rec-specific
    for label, elig in [("Rec A", ea), ("Rec B", eb)]:
        for group in elig.disjunctive_groups:
            if group.conditions:
                _add_req(_display_code(group.conditions[0]))
            elif group.observations:
                obs = group.observations[0]
                _add_req(_format_obs_short(obs))

    # Required observations (conjunctive, non-disjunctive)
    for label, elig in [("Rec A", ea), ("Rec B", eb)]:
        for obs in elig.required_observations:
            _add_req(_format_obs_short(obs))

    # Risk scores
    for rs in ea.risk_scores + eb.risk_scores:
        comp = _comparator_symbol(rs.get("comparator", ""))
        _add_req(f"{rs.get('name')} {comp} {rs.get('threshold')}%")

    # Smoking
    for label, elig in [("Rec A", ea), ("Rec B", eb)]:
        if elig.smoking_status:
            _add_req(f"smoking status: {elig.smoking_status[0]}")

    # --- Build the exclusion constraints (union) ---
    excl_parts: list[str] = []
    excl_seen: set[str] = set()

    def _add_excl(text: str) -> None:
        if text not in excl_seen:
            excl_seen.add(text)
            excl_parts.append(text)

    for c in ea.excluded_conditions + eb.excluded_conditions:
        _add_excl(_display_code(c))

    for obs in ea.excluded_observations + eb.excluded_observations:
        _add_excl(_format_obs_short(obs))

    for m in ea.excluded_medications + eb.excluded_medications:
        _add_excl(f"active {_display_code(m)}")

    # --- Assemble the sentence ---
    scenario = f"A {mid_age}-year-old"

    if req_parts:
        scenario += f" with {', '.join(req_parts)}"

    if excl_parts:
        scenario += f" (without {', '.join(excl_parts[:3])}"
        if len(excl_parts) > 3:
            scenario += f", +{len(excl_parts) - 3} more"
        scenario += ")"

    g_a = _short_guideline(rec_a.guideline_id)
    g_b = _short_guideline(rec_b.guideline_id)
    scenario += (
        f" would trigger both the {g_a} rec "
        f"({_short_title(rec_a.title)}) and the "
        f"{g_b} rec ({_short_title(rec_b.title)})."
    )

    return scenario


def _format_obs_short(obs: dict) -> str:
    """Format an observation requirement as a compact string."""
    comp = _comparator_symbol(obs.get("comparator", ""))
    code = _display_code(obs.get("code", ""))
    threshold = obs.get("threshold", "")
    unit = obs.get("unit", "")
    return f"{code} {comp} {threshold} {unit}".strip()


_STATIN_IDS = {
    "med:atorvastatin", "med:rosuvastatin", "med:simvastatin",
    "med:pravastatin", "med:lovastatin", "med:fluvastatin", "med:pitavastatin",
}


@dataclass
class VerdictGuess:
    """Pre-populated verdict and rationale for a pair."""
    verdict: str  # preempted_by, modifies, convergence, reject
    rationale: str
    # For preempted_by: (winner, loser)
    winner: RecInfo | None = None
    loser: RecInfo | None = None
    # For modifies: (modifier, target, nature)
    modifier: RecInfo | None = None
    target: RecInfo | None = None
    nature: str | None = None


def _classify_verdict(
    rec_a: RecInfo,
    rec_b: RecInfo,
    overlap: OverlapAnalysis,
) -> VerdictGuess:
    """Determine the most likely verdict based on pair characteristics."""

    # --- No interaction ---
    if overlap.candidate_type == "no_interaction":
        return VerdictGuess(
            verdict="reject",
            rationale="Eligibility criteria do not overlap — no patient can trigger both recs.",
        )

    a_entities = set(rec_a.action_entity_ids)
    b_entities = set(rec_b.action_entity_ids)
    shared = a_entities & b_entities

    a_statins = a_entities & _STATIN_IDS
    b_statins = b_entities & _STATIN_IDS
    shared_statins = a_statins & b_statins

    a_is_statin_rec = len(a_statins) > 0 and len(a_statins) >= len(a_entities) / 2
    b_is_statin_rec = len(b_statins) > 0 and len(b_statins) >= len(b_entities) / 2

    g_a = _short_guideline(rec_a.guideline_id)
    g_b = _short_guideline(rec_b.guideline_id)

    ea = rec_a.eligibility or EligibilityCriteria()
    eb = rec_b.eligibility or EligibilityCriteria()

    # --- Both are statin recs with shared statin targets ---
    if a_is_statin_rec and b_is_statin_rec and shared_statins:

        # KDIGO statin-for-CKD vs ACC/AHA high-intensity strategies:
        # KDIGO explicitly recommends moderate-intensity in CKD. If ACC/AHA
        # offers high-intensity (atorvastatin + rosuvastatin only), KDIGO
        # modifies to moderate.
        kdigo_rec = None
        other_rec = None
        if "kdigo" in rec_a.guideline_id:
            kdigo_rec, other_rec = rec_a, rec_b
        elif "kdigo" in rec_b.guideline_id:
            kdigo_rec, other_rec = rec_b, rec_a

        if kdigo_rec and "statin-for-ckd" in kdigo_rec.id:
            other_statins = set(other_rec.action_entity_ids) & _STATIN_IDS
            # ACC/AHA high-intensity strategies have only atorvastatin + rosuvastatin
            if other_statins == {"med:atorvastatin", "med:rosuvastatin"}:
                return VerdictGuess(
                    verdict="modifies",
                    modifier=kdigo_rec,
                    target=other_rec,
                    nature="intensity_reduction",
                    rationale=(
                        f"KDIGO recommends moderate-intensity statin in CKD G3-G5 "
                        f"due to altered pharmacokinetics and increased myopathy risk. "
                        f"The {_short_guideline(other_rec.guideline_id)} rec offers high-intensity; "
                        f"KDIGO adjusts to moderate for the CKD overlap population."
                    ),
                )
            # Both are moderate-intensity statin recs → convergence
            if other_statins == _STATIN_IDS or len(other_statins) == 7:
                return VerdictGuess(
                    verdict="convergence",
                    rationale=(
                        f"Both recs recommend moderate-intensity statin therapy for the "
                        f"overlap population. No conflict — the shared entity layer "
                        f"deduplicates. No cross-edge needed."
                    ),
                )

        # USPSTF vs ACC/AHA statin recs: both are statin recommendations.
        # ACC/AHA provides more granular guidance (specific benefit groups,
        # intensity tiers). For the overlap population, ACC/AHA preempts USPSTF.
        uspstf_rec = None
        accaha_rec = None
        if "uspstf" in rec_a.guideline_id and "acc-aha" in rec_b.guideline_id:
            uspstf_rec, accaha_rec = rec_a, rec_b
        elif "acc-aha" in rec_a.guideline_id and "uspstf" in rec_b.guideline_id:
            accaha_rec, uspstf_rec = rec_a, rec_b

        if uspstf_rec and accaha_rec:
            return VerdictGuess(
                verdict="preempted_by",
                winner=accaha_rec,
                loser=uspstf_rec,
                rationale=(
                    f"ACC/AHA provides more granular, domain-specific guidance "
                    f"(specific statin benefit groups with intensity tiers) than "
                    f"the USPSTF population-level screening recommendation. "
                    f"Per ADR 0018, specialty society guideline (priority 200) "
                    f"preempts federal task force (priority 100) within the "
                    f"cardiovascular domain."
                ),
            )

        # KDIGO statin-for-CKD vs USPSTF: both moderate-intensity → convergence
        if kdigo_rec and "uspstf" in (other_rec or rec_a).guideline_id:
            return VerdictGuess(
                verdict="convergence",
                rationale=(
                    f"Both recs recommend moderate-intensity statin therapy. "
                    f"KDIGO is CKD-specific; USPSTF is population-level. "
                    f"For the overlap population they agree — no conflict, "
                    f"no cross-edge needed."
                ),
            )

        # Generic statin convergence fallback
        return VerdictGuess(
            verdict="convergence",
            rationale=(
                f"Both recs prescribe overlapping statin medications for the "
                f"overlap population. No intensity conflict detected. "
                f"Shared entity layer handles deduplication."
            ),
        )

    # --- Shared non-statin targets ---
    if shared and not shared_statins:
        # Shared observations (e.g., both require eGFR monitoring)
        winner, loser = _guess_preemption_direction(rec_a, rec_b)
        return VerdictGuess(
            verdict="convergence",
            rationale=(
                f"Both recs target shared entities but in different clinical "
                f"contexts. The shared entity layer handles deduplication."
            ),
        )

    # --- No shared targets: different therapeutic domains ---
    if not shared:
        # Check if the domains are truly unrelated
        a_domain = _therapeutic_domain(rec_a)
        b_domain = _therapeutic_domain(rec_b)

        if a_domain != b_domain:
            return VerdictGuess(
                verdict="reject",
                rationale=(
                    f"Different therapeutic domains ({a_domain} vs {b_domain}). "
                    f"Both recs can co-fire for the overlap population but address "
                    f"independent clinical concerns. No interaction edge needed."
                ),
            )

        # Same domain but no shared entities — unusual, flag for review
        modifier, target = _guess_modification_direction(rec_a, rec_b)
        return VerdictGuess(
            verdict="reject",
            rationale=(
                f"Both recs address the {a_domain} domain but prescribe "
                f"different actions with no shared therapeutic targets. "
                f"Likely independent — review if a MODIFIES relationship applies."
            ),
        )

    # --- Fallback: mixed shared targets ---
    modifier, target = _guess_modification_direction(rec_a, rec_b)
    return VerdictGuess(
        verdict="convergence",
        rationale=(
            f"Shared therapeutic targets detected. Review whether one rec "
            f"preempts the other or if the shared entity layer handles this."
        ),
    )


def _therapeutic_domain(rec: RecInfo) -> str:
    """Classify a rec into a broad therapeutic domain for reject rationale."""
    entities = set(rec.action_entity_ids)
    if entities & _STATIN_IDS:
        return "lipid management"
    if entities & {"med:empagliflozin", "med:dapagliflozin"}:
        return "SGLT2i / renal protection"
    if entities & {"med:lisinopril", "med:enalapril", "med:ramipril",
                   "med:losartan", "med:valsartan", "med:irbesartan"}:
        return "RAS blockade / renal protection"
    if entities & {"obs:egfr", "obs:urine-acr"}:
        return "CKD monitoring"
    if entities & {"proc:sdm-statin-discussion"}:
        return "shared decision-making"
    return rec.intent or "unclassified"


def _render_verdict(
    lines: list[str],
    rec_a: RecInfo,
    rec_b: RecInfo,
    overlap: OverlapAnalysis,
    g_a: str,
    g_b: str,
) -> None:
    """Render the pre-populated verdict section with checked option and rationale."""
    guess = _classify_verdict(rec_a, rec_b, overlap)

    lines.append("### Verdict")
    lines.append("")

    if guess.verdict == "reject":
        lines.append("- [x] **Reject**")
        _render_other_options(lines, rec_a, rec_b, overlap, checked=None)
        lines.append("")
        lines.append(f"**Rationale:** {guess.rationale}")
        lines.append("")
        return

    if guess.verdict == "preempted_by":
        winner = guess.winner or rec_a
        loser = guess.loser or rec_b
        w_g = _short_guideline(winner.guideline_id)
        l_g = _short_guideline(loser.guideline_id)
        lines.append(f"- [x] **PREEMPTED_BY:** {w_g} ({_short_title(winner.title)}) preempts {l_g} ({_short_title(loser.title)})")
        lines.append(f"  - Edge: `({loser.id})-[:PREEMPTED_BY]->({winner.id})`")
        _render_other_options(lines, rec_a, rec_b, overlap, checked="preempted_by")

    elif guess.verdict == "modifies":
        modifier = guess.modifier or rec_a
        target = guess.target or rec_b
        m_g = _short_guideline(modifier.guideline_id)
        t_g = _short_guideline(target.guideline_id)
        nature = guess.nature or "___"
        lines.append(f"- [x] **MODIFIES:** {m_g} ({_short_title(modifier.title)}) modifies {t_g} ({_short_title(target.title)}); nature: `{nature}`")
        lines.append(f"  - Edge: `({modifier.id})-[:MODIFIES]->({target.id})`")
        _render_other_options(lines, rec_a, rec_b, overlap, checked="modifies")

    elif guess.verdict == "convergence":
        lines.append("- [x] **Convergence only** — no edge needed, shared entity layer handles it")
        _render_other_options(lines, rec_a, rec_b, overlap, checked="convergence")

    lines.append("")
    lines.append(f"**Rationale:** {guess.rationale}")
    lines.append("")


def _render_other_options(
    lines: list[str],
    rec_a: RecInfo,
    rec_b: RecInfo,
    overlap: OverlapAnalysis,
    checked: str | None,
) -> None:
    """Render the unchecked alternative verdict options."""
    if checked != "preempted_by":
        winner, loser = _guess_preemption_direction(rec_a, rec_b)
        w_g = _short_guideline(winner.guideline_id)
        l_g = _short_guideline(loser.guideline_id)
        lines.append(f"- [ ] **PREEMPTED_BY:** {w_g} ({_short_title(winner.title)}) preempts {l_g} ({_short_title(loser.title)})")
    if checked != "modifies":
        modifier, target = _guess_modification_direction(rec_a, rec_b)
        m_g = _short_guideline(modifier.guideline_id)
        t_g = _short_guideline(target.guideline_id)
        lines.append(f"- [ ] **MODIFIES:** {m_g} ({_short_title(modifier.title)}) modifies {t_g} ({_short_title(target.title)}); nature: ___")
    if checked != "convergence" and overlap.shared_therapeutic_targets:
        lines.append("- [ ] **Convergence only** — no edge needed")
    if checked != "reject":
        lines.append("- [ ] **Reject** — no clinically meaningful interaction")


def _eligibility_requires(ec: EligibilityCriteria) -> str:
    """Compact requirements string for the comparison table."""
    parts: list[str] = []

    if ec.required_conditions:
        parts.append(", ".join(_display_code(c) for c in ec.required_conditions))

    for group in ec.disjunctive_groups:
        or_items: list[str] = []
        for c in group.conditions:
            or_items.append(_display_code(c))
        for obs in group.observations:
            comp = _comparator_symbol(obs.get("comparator", ""))
            or_items.append(f"{_display_code(obs['code'])} {comp} {obs.get('threshold')}")
        for m in group.medications:
            or_items.append(f"active {_display_code(m)}")
        for sv in group.smoking_values:
            or_items.append(f"smoking: {sv}")
        if or_items:
            parts.append(f"ANY OF [{' ∣ '.join(or_items)}]")

    for obs in ec.required_observations:
        comp = _comparator_symbol(obs.get("comparator", ""))
        parts.append(f"{_display_code(obs['code'])} {comp} {obs.get('threshold')} {obs.get('unit', '')}")

    if ec.required_medications:
        parts.append("Active: " + ", ".join(_display_code(m) for m in ec.required_medications))

    for rs in ec.risk_scores:
        comp = _comparator_symbol(rs.get("comparator", ""))
        parts.append(f"{rs.get('name')} {comp} {rs.get('threshold')}")

    if ec.smoking_status:
        parts.append(f"Smoking: {', '.join(ec.smoking_status)}")

    return "; ".join(parts) if parts else "—"


def _eligibility_excludes(ec: EligibilityCriteria) -> str:
    """Compact exclusions string for the comparison table."""
    parts: list[str] = []

    if ec.excluded_conditions:
        parts.append(", ".join(_display_code(c) for c in ec.excluded_conditions))

    for obs in ec.excluded_observations:
        comp = _comparator_symbol(obs.get("comparator", ""))
        parts.append(f"{_display_code(obs['code'])} {comp} {obs.get('threshold')} {obs.get('unit', '')}")

    if ec.excluded_medications:
        parts.append("Active: " + ", ".join(_display_code(m) for m in ec.excluded_medications))

    return "; ".join(parts) if parts else "—"


# Default priority by guideline (per ADR 0018)
_GUIDELINE_PRIORITY = {
    "guideline:uspstf-statin-2022": 100,
    "guideline:acc-aha-cholesterol-2018": 200,
    "guideline:kdigo-ckd-2024": 200,
}


def _guess_preemption_direction(
    rec_a: RecInfo, rec_b: RecInfo
) -> tuple[RecInfo, RecInfo]:
    """Guess which rec preempts. Returns (winner, loser). Higher priority wins."""
    pri_a = _GUIDELINE_PRIORITY.get(rec_a.guideline_id, 100)
    pri_b = _GUIDELINE_PRIORITY.get(rec_b.guideline_id, 100)
    if pri_a >= pri_b:
        return rec_a, rec_b
    return rec_b, rec_a


def _guess_modification_direction(
    rec_a: RecInfo, rec_b: RecInfo
) -> tuple[RecInfo, RecInfo]:
    """Guess which rec modifies the other. Returns (modifier, target).
    KDIGO typically modifies USPSTF/ACC-AHA. Specialty modifies general."""
    # KDIGO modifies others
    if "kdigo" in rec_a.guideline_id:
        return rec_a, rec_b
    if "kdigo" in rec_b.guideline_id:
        return rec_b, rec_a
    # ACC/AHA modifies USPSTF
    pri_a = _GUIDELINE_PRIORITY.get(rec_a.guideline_id, 100)
    pri_b = _GUIDELINE_PRIORITY.get(rec_b.guideline_id, 100)
    if pri_a >= pri_b:
        return rec_a, rec_b
    return rec_b, rec_a


def _short_guideline(guideline_id: str) -> str:
    """Short display name for a guideline."""
    return {
        "guideline:uspstf-statin-2022": "USPSTF",
        "guideline:acc-aha-cholesterol-2018": "ACC/AHA",
        "guideline:kdigo-ckd-2024": "KDIGO",
    }.get(guideline_id, guideline_id)


def _short_title(title: str) -> str:
    """Truncate a rec title for inline use."""
    if len(title) > 60:
        return title[:57] + "..."
    return title


def generate_readme(output_dir: Path) -> None:
    """Generate docs/review/README.md with clinician reviewer instructions."""
    readme_path = output_dir / "README.md"
    content = """\
# Cross-guideline interaction review

This directory contains the output of `scripts/discover-interactions.py`.
The tool identifies Recommendation pairs across guidelines whose eligibility
criteria overlap (same patient could match both) and pre-populates a review
document for clinician sign-off.

## Document layout

`interaction-candidates.md` is grouped into three sections:

1. **Convergence candidates** — both recs prescribe the same medication(s).
   Likely verdict: PREEMPTED_BY or convergence-only.
2. **Modification candidates** — both recs fire for the same patient but
   target different actions. Likely verdict: MODIFIES or reject.
3. **No interaction (obvious rejects)** — eligibility doesn't overlap.
   Pre-checked as reject.

Each pair shows:
- A **clinical scenario** sentence describing a concrete patient who would
  trigger both recs.
- A **side-by-side comparison table** (guideline, grade, age, requires,
  excludes, actions) so you can visually diff the two recs.
- A **pre-populated verdict** with the most likely direction already filled
  in based on guideline priority (ADR 0018). Check or uncheck; add rationale.

## How to review

For each pair, read the clinical scenario, scan the comparison table, then:

1. **Check one box** on the verdict. The pre-populated option is the tool's
   best guess — override freely.
2. **Fill in the rationale** �� one sentence explaining why.
3. For MODIFIES verdicts, pick a `nature` value from the options listed.

## Verdict types

| Verdict | When to use | Graph effect |
|---------|-------------|--------------|
| **PREEMPTED_BY** | One rec fully supersedes the other for the overlapping population. | `(loser)-[:PREEMPTED_BY]->(winner)` edge. Loser dimmed in UI. |
| **MODIFIES** | Both recs fire, but one adjusts the other's intensity/dose/monitoring. | `(modifier)-[:MODIFIES]->(target)` edge. Both remain active. |
| **Convergence only** | Same action, but neither preempts — shared entity layer handles it. | No edge. |
| **Reject** | Co-match is possible but no clinically meaningful interaction. | No edge. |

## MODIFIES nature values

| Nature | Meaning |
|--------|---------|
| `intensity_reduction` | Strategy-level: e.g., high -> moderate intensity statin. |
| `dose_adjustment` | Medication-level change within a chosen intensity. |
| `monitoring` | Additional monitoring required when the target rec fires. |
| `contraindication_warning` | Source condition creates a relative contraindication. |

## Edge direction conventions

- **PREEMPTED_BY:** edge points FROM the loser TO the winner.
  "ACC/AHA preempts USPSTF" = `(uspstf-rec)-[:PREEMPTED_BY]->(accaha-rec)`.
- **MODIFIES:** edge points FROM the modifier TO the target.
  "KDIGO modifies ACC/AHA" = `(kdigo-rec)-[:MODIFIES]->(accaha-rec)`.

## Re-running

```sh
python scripts/discover-interactions.py --from-seeds
```

This **overwrites** the entire document. Back up your verdicts before
re-running if you've already reviewed pairs.
"""
    readme_path.write_text(content)


def _get_seed_files(guideline_filter: set[str] | None) -> list[Path]:
    """Get the list of seed files to parse, filtered by --guidelines flag."""
    if guideline_filter:
        filenames = []
        for g in guideline_filter:
            fname = GUIDELINE_FLAG_MAP.get(g)
            if fname:
                filenames.append(fname)
            else:
                print(f"Warning: unknown guideline '{g}'. Known: {', '.join(GUIDELINE_FLAG_MAP.keys())}", file=sys.stderr)
        return [SEEDS_DIR / f for f in filenames if (SEEDS_DIR / f).exists()]
    else:
        # All guideline seed files (exclude cross-edges, constraints, clinical-entities)
        return [
            f
            for f in sorted(SEEDS_DIR.glob("*.cypher"))
            if f.name not in ("constraints.cypher", "clinical-entities.cypher")
            and not f.name.startswith("cross-edges-")
        ]


def _extract_prop(block: str, prop_name: str) -> str | None:
    """Extract a Cypher property value from an ON CREATE SET block."""
    # Match: prop_name = 'value' (single-quoted string)
    pattern = rf"\w+\.{prop_name}\s*=\s*'((?:[^'\\]|\\.)*)'"
    match = re.search(pattern, block)
    if match:
        return match.group(1).replace("\\'", "'")
    return None



def _format_candidate_type(ct: str) -> str:
    return {
        "convergence": "**Convergence** (shared therapeutic targets → potential PREEMPTED_BY or reinforcing)",
        "modification": "**Modification** (different therapeutic actions, same patient → potential MODIFIES)",
        "no_interaction": "**No interaction** (eligibility does not overlap)",
        "manual_review": "**Manual review needed** (complex predicates could not be fully analyzed)",
    }.get(ct, ct)


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover cross-guideline interaction candidates."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-seeds",
        action="store_true",
        help="Parse seed .cypher files directly (no Neo4j required)",
    )
    source.add_argument(
        "--from-graph",
        action="store_true",
        help="Query a running Neo4j instance",
    )
    parser.add_argument(
        "--guidelines",
        type=str,
        default=None,
        help="Comma-separated guideline names to include (e.g., statins,cholesterol,kdigo). Default: all.",
    )

    args = parser.parse_args()

    guideline_filter = None
    if args.guidelines:
        guideline_filter = set(args.guidelines.split(","))

    print("Loading recommendations...")
    if args.from_seeds:
        recs = parse_recs_from_seeds(guideline_filter)
    else:
        recs = parse_recs_from_graph()

    print(f"Found {len(recs)} recommendations across {len(set(r.guideline_id for r in recs))} guidelines:")
    for gid in sorted(set(r.guideline_id for r in recs)):
        count = sum(1 for r in recs if r.guideline_id == gid)
        print(f"  {GUIDELINE_DISPLAY.get(gid, gid)}: {count} recs")

    print("\nAnalyzing cross-guideline pairs...")
    output_path = OUTPUT_DIR / "interaction-candidates.md"
    pairs = generate_review_document(recs, output_path)

    overlapping = sum(1 for _, _, o in pairs if o.age_overlaps and o.condition_compatible)
    print(f"\nResults:")
    print(f"  Total cross-guideline pairs: {len(pairs)}")
    print(f"  Pairs with eligibility overlap: {overlapping}")
    print(f"  Pairs with no overlap: {len(pairs) - overlapping}")
    print(f"\nOutput written to: {output_path}")

    # Generate README
    generate_readme(OUTPUT_DIR)
    print(f"Reviewer instructions written to: {OUTPUT_DIR / 'README.md'}")


if __name__ == "__main__":
    main()
