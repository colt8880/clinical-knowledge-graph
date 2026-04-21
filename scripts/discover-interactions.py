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

    # Check if A requires a condition B excludes, or vice versa
    a_req = set(ea.required_conditions)
    a_exc = set(ea.excluded_conditions)
    b_req = set(eb.required_conditions)
    b_exc = set(eb.excluded_conditions)

    conflict_ab = a_req & b_exc
    conflict_ba = b_req & a_exc

    if conflict_ab:
        condition_compatible = False
        names = ", ".join(_display_code(c) for c in conflict_ab)
        condition_notes_parts.append(
            f"Rec A requires {names} which Rec B excludes"
        )
    if conflict_ba:
        condition_compatible = False
        names = ", ".join(_display_code(c) for c in conflict_ba)
        condition_notes_parts.append(
            f"Rec B requires {names} which Rec A excludes"
        )

    # Shared required conditions
    shared_req = a_req & b_req
    if shared_req:
        names = ", ".join(_display_code(c) for c in shared_req)
        condition_notes_parts.append(f"Both require: {names}")

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

    # Sort: overlapping pairs first, then by guideline pair, then by rec ID
    pairs.sort(
        key=lambda p: (
            not p[2].age_overlaps or not p[2].condition_compatible,
            p[0].guideline_id,
            p[1].guideline_id,
            p[0].id,
            p[1].id,
        )
    )

    # Generate markdown
    lines: list[str] = []
    lines.append("# Cross-guideline interaction candidates")
    lines.append("")
    lines.append(
        f"Generated by `scripts/discover-interactions.py --from-seeds` on "
        f"{_today()}."
    )
    lines.append("")
    lines.append(
        "This document lists all cross-guideline Recommendation pairs whose "
        "eligibility criteria may overlap, meaning the same patient could match "
        "both Recs simultaneously. For each pair, the tool provides mechanical "
        "overlap analysis. The **Clinician verdict** and **Clinician rationale** "
        "fields are blank — they must be filled by a clinician reviewer."
    )
    lines.append("")
    lines.append(f"**Total candidate pairs:** {len(pairs)}")
    overlapping = sum(1 for _, _, o in pairs if o.age_overlaps and o.condition_compatible)
    lines.append(f"**Pairs with eligibility overlap:** {overlapping}")
    no_overlap = len(pairs) - overlapping
    lines.append(f"**Pairs with no overlap (reject obvious):** {no_overlap}")
    lines.append("")
    lines.append("See `docs/review/README.md` for reviewer instructions.")
    lines.append("")
    lines.append("---")
    lines.append("")

    for idx, (rec_a, rec_b, overlap) in enumerate(pairs, 1):
        ea = rec_a.eligibility or EligibilityCriteria()
        eb = rec_b.eligibility or EligibilityCriteria()

        lines.append(f"## Pair {idx}: {rec_a.id} ↔ {rec_b.id}")
        lines.append("")

        # Source Rec
        lines.append("### Source Rec")
        lines.append("")
        lines.append(f"- **ID:** `{rec_a.id}`")
        lines.append(
            f"- **Guideline:** {GUIDELINE_DISPLAY.get(rec_a.guideline_id, rec_a.guideline_id)}"
        )
        lines.append(f"- **Title:** {rec_a.title}")
        lines.append(f"- **Evidence grade:** {rec_a.evidence_grade}")
        lines.append(f"- **Intent:** {rec_a.intent}")
        lines.append(f"- **Source section:** {rec_a.source_section}")
        lines.append(f"- **Eligibility:** {eligibility_to_plain_english(ea)}")
        lines.append("")

        # Target Rec
        lines.append("### Target Rec")
        lines.append("")
        lines.append(f"- **ID:** `{rec_b.id}`")
        lines.append(
            f"- **Guideline:** {GUIDELINE_DISPLAY.get(rec_b.guideline_id, rec_b.guideline_id)}"
        )
        lines.append(f"- **Title:** {rec_b.title}")
        lines.append(f"- **Evidence grade:** {rec_b.evidence_grade}")
        lines.append(f"- **Intent:** {rec_b.intent}")
        lines.append(f"- **Source section:** {rec_b.source_section}")
        lines.append(f"- **Eligibility:** {eligibility_to_plain_english(eb)}")
        lines.append("")

        # Overlap analysis
        lines.append("### Overlap analysis")
        lines.append("")
        lines.append(f"- **Age range intersection:** {overlap.age_overlap}")
        lines.append(f"- **Condition compatibility:** {overlap.condition_notes}")
        if overlap.shared_therapeutic_targets:
            targets_str = ", ".join(
                f"`{t}`" for t in overlap.shared_therapeutic_targets
            )
            lines.append(f"- **Shared therapeutic targets:** {targets_str}")
        else:
            lines.append("- **Shared therapeutic targets:** None")
        lines.append(f"- **Candidate interaction type:** {_format_candidate_type(overlap.candidate_type)}")
        if overlap.notes:
            for note in overlap.notes:
                lines.append(f"- **Note:** {note}")
        lines.append("")

        # Clinician verdict section
        lines.append("### Clinician review")
        lines.append("")
        lines.append("- **Verdict:** _pending_")
        lines.append("  - [ ] Approve as PREEMPTED_BY (direction: ___ preempts ___)")
        lines.append("  - [ ] Approve as MODIFIES (direction: ___ modifies ___; nature: ___)")
        lines.append("  - [ ] Convergence only (no edge needed; handled by shared entity layer)")
        lines.append("  - [ ] Reject (no clinically meaningful interaction)")
        lines.append("- **Rationale:** ")
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    return pairs


def generate_readme(output_dir: Path) -> None:
    """Generate docs/review/README.md with clinician reviewer instructions."""
    readme_path = output_dir / "README.md"
    content = """\
# Cross-guideline interaction review

This directory contains the output of `scripts/discover-interactions.py` — a
tool that identifies Recommendation pairs across different guidelines whose
eligibility criteria overlap, meaning the same patient could potentially match
both.

## For the clinician reviewer

The tool does the mechanical work: parsing predicates, computing age range
overlap, identifying shared therapeutic targets. **You** do the clinical
judgment: deciding whether two co-matching Recs represent a meaningful
interaction that should be encoded in the graph.

### What to review

`interaction-candidates.md` contains one section per candidate pair. Each
section shows:

- **Source Rec / Target Rec:** The two Recommendations, with their guideline,
  evidence grade, and eligibility criteria rendered as plain English.
- **Overlap analysis:** Where the two Recs' eligibility overlaps (age range
  intersection, condition compatibility, shared therapeutic targets).
- **Candidate interaction type:** The tool's mechanical classification
  (convergence, modification, or no interaction). This is a suggestion, not
  a verdict.
- **Clinician review:** Blank fields for your verdict and rationale.

### Decision criteria

For each pair, choose one:

| Verdict | When to use | What happens |
|---------|-------------|--------------|
| **PREEMPTED_BY** | One Rec fully supersedes the other for the overlapping population. The preempted Rec adds no clinical value when the winner fires. | A `PREEMPTED_BY` edge is added. The preempted Rec is dimmed in the UI and annotated in the trace. |
| **MODIFIES** | Both Recs fire, but one adjusts the other's intensity, dose, or monitoring. Neither replaces the other. | A `MODIFIES` edge is added with a `nature` (intensity_reduction, dose_adjustment, monitoring, contraindication_warning). Both Recs remain active. |
| **Convergence only** | Both Recs recommend the same action (shared therapeutic targets) but neither preempts the other. The shared entity layer already handles this — no cross-edge needed. | No edge added. The existing convergence detection (F33) handles this case. |
| **Reject** | The two Recs can theoretically co-match but address unrelated clinical domains. No meaningful interaction. | No edge added. |

### Preemption direction

`PREEMPTED_BY` edges point FROM the preempted (losing) Rec TO the winning Rec.
When filling in the verdict, specify: "Rec A preempts Rec B" means the edge
goes `(B)-[:PREEMPTED_BY]->(A)`.

Per ADR 0018, the winning Rec typically has higher `priority` (specialty society
guidelines default to 200; USPSTF defaults to 100).

### MODIFIES nature values

| Nature | Meaning |
|--------|---------|
| `intensity_reduction` | Strategy-level change: e.g., high → moderate intensity statin. |
| `dose_adjustment` | Medication-level change within a chosen intensity. |
| `monitoring` | Additional monitoring required when the target Rec fires. |
| `contraindication_warning` | The source condition creates a relative contraindication. |

New nature values require an ADR and schema update (ADR 0019).

### What "overlapping eligibility" means concretely

Two Recs have overlapping eligibility when there exists at least one
hypothetical patient who satisfies both Recs' `structured_eligibility`
predicates simultaneously. The tool checks:

1. **Age range intersection.** If Rec A covers 40–75 and Rec B covers 18–75,
   the overlap is 40–75.
2. **Condition compatibility.** If Rec A requires `cond:ascvd-established` and
   Rec B excludes it, no patient can satisfy both — no overlap.
3. **Shared therapeutic targets.** If both Recs' strategies include the same
   Medication or Observation nodes, they converge on the same clinical action.

Pairs flagged "no eligibility overlap" are obvious rejects — the age ranges
don't intersect or one Rec requires a condition the other excludes.

### Re-running the tool

When a new guideline is added, re-run:

```sh
python scripts/discover-interactions.py --from-seeds
```

The tool regenerates the entire document but does NOT overwrite existing
clinician verdicts. If you have already reviewed pairs, back up your verdicts
before re-running, then merge them back in. (A future version may preserve
existing verdicts automatically.)

### Examples

**Preemption example:** ACC/AHA secondary prevention (high-intensity statin for
established ASCVD) preempts USPSTF Grade B (moderate-intensity statin for
primary prevention). A patient with established ASCVD triggers the ACC/AHA Rec;
the USPSTF Rec's exclusion of established ASCVD means it won't fire for the
same patient, but if the exclusion were loosened, ACC/AHA would take precedence.

**Modification example:** KDIGO statin-for-CKD modifies ACC/AHA high-intensity
strategies. A CKD patient eligible for ACC/AHA high-intensity statin should
receive moderate-intensity per KDIGO due to altered pharmacokinetics. The
ACC/AHA Rec still fires; the KDIGO Rec annotates it.

**Reject example:** KDIGO ACEi/ARB for CKD and USPSTF statin Grade B. Both can
co-match (a 55-year-old with CKD and CVD risk factors), but they address
completely different therapeutic domains (renal protection vs CV prevention).
No interaction edge needed.
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


def _display_code(code: str) -> str:
    """Convert a graph node ID to readable display."""
    if ":" in code:
        _, name = code.split(":", 1)
        return name.replace("-", " ").title()
    return code


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
