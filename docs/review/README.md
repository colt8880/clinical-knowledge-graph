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
