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
