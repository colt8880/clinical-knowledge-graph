# 0020. Three-arm eval methodology

Status: Accepted
Date: 2026-04-20
Supersedes: None
Paired with: F27 (full harness run + thesis test)

## Context

v1 adds two guidelines (ACC/AHA 2018 Cholesterol, KDIGO 2024 CKD) alongside the v0 USPSTF 2022 statin model and stands up a three-arm eval harness (F22). The harness measures whether graph-retrieved context produces better clinical recommendations than vanilla LLM knowledge or flat RAG.

The original plan tested this via cross-guideline edges (PREEMPTED_BY, MODIFIES). Those edges were removed pending clinician review after modeling errors were found (see `docs/ISSUES.md`). The thesis now measures **convergence visibility**: the graph's ability to surface that multiple guidelines independently recommend the same therapeutic actions via shared clinical entities.

This ADR documents the methodology, margin, judge pinning, and failure handling for the v1 thesis gate.

## Decision

### Thesis statement

**Arm C (graph-context LLM) beats Arm B (flat RAG LLM) on the multi-guideline fixture subset by ≥ 0.5 composite points on a 1-5 scale.**

The hypothesis: Arm C's explicit convergence summary — "three guidelines independently recommend moderate-intensity statin for this patient, via these pathways" — anchors the LLM to multi-source clinical agreement, producing better Integration scores than Arm B's disconnected prose chunks. Flat RAG retrieves guideline text but cannot structurally identify that separate guidelines target the same medications.

### Three arms

| Arm | ID | Context supplied to LLM |
|-----|-----|-------------------------|
| A | `a` | `PatientContext` only. No guideline material. Tests LLM training knowledge. |
| B | `b` | `PatientContext` + top-k chunks from guideline prose (flat RAG). |
| C | `c` | `PatientContext` + graph-retrieved context: serialized EvalTrace summary + subgraph + convergence summary. |

All arms use the same LLM (`claude-sonnet-4-6-20250514`), same system prompt, temperature 0, same max tokens. Only the context input varies.

### Fixture subsets

| Subset | Fixtures | Count | Purpose |
|--------|----------|-------|---------|
| Single-guideline (statins) | `evals/fixtures/statins/case-01` through `case-05` | 5 | Baseline |
| Single-guideline (cholesterol) | `evals/fixtures/cholesterol/case-01` through `case-04` | 4 | Baseline |
| Single-guideline (KDIGO) | `evals/fixtures/kdigo/case-01` through `case-03` | 3 | Baseline |
| Multi-guideline | `evals/fixtures/cross-domain/case-01` through `case-04` | 4 | **Thesis differentiator** |
| **Total** | | **16** | |

### Scoring rubric

Four dimensions, 1-5 each. Composite = arithmetic mean (no weighting). Defined in `evals/rubric.md` (rubric version `v1`).

1. **Completeness** — are all expected actions present?
2. **Clinical Appropriateness** — are recommendations safe and correct?
3. **Prioritization** — is sequencing reasonable?
4. **Integration** — does the output correctly handle cross-guideline interactions?

Integration is the primary differentiator on multi-guideline fixtures. On single-guideline fixtures, Integration scores 5 by default for all arms.

### Judge model

Claude Opus 4.6 (`claude-opus-4-6-20250610`), temperature 0. Separate from the arm model to avoid self-preference bias.

### Preregistered margin

**Arm C mean composite on the multi-guideline subset (4 fixtures) must exceed Arm B's mean composite by ≥ 0.5 points.**

Concrete example: if Arm B mean composite on multi-guideline fixtures is 3.2, Arm C must be ≥ 3.7 to pass.

This margin is not adjusted during F27. If it needs changing, that's a new ADR + new rubric version.

### Self-consistency check

Run the judge 3 times on the full fixture set (3 runs × 16 fixtures × 3 arms = 144 scoring calls). Report:

- Mean composite per arm per subset across 3 runs.
- Standard deviation of composite per arm per subset.
- If SD > 0.3 on any arm/subset combination, flag rubric instability in the report.

Self-consistency ensures the margin is meaningful — a 0.5-point gap isn't credible if the judge's own variance exceeds 0.3.

### Pass/fail criteria

**PASS:** Arm C mean composite on multi-guideline subset > Arm B mean composite on multi-guideline subset by ≥ 0.5, AND no self-consistency SD > 0.3 on any arm/subset.

**FAIL:** Either the margin is not met, or self-consistency is violated. In either case, the scorecard documents:

1. Per-dimension gap analysis (which of the 4 dimensions is underperforming).
2. Per-fixture breakdown (which specific cases are failing).
3. Hypotheses: serialization gap, retrieval gap, fixture construction gap, or genuine null result.
4. Recommended next feature(s) to address the gap.

Ship the report regardless. A failed thesis gate is a result, not a bug.

### Interpreting edge cases

| Scenario | Interpretation | Action |
|----------|---------------|--------|
| Arm C wins by ≥ 0.5 | PASS. Thesis confirmed. | v1 thesis-complete. |
| Arm C wins by 0.1-0.4 | Signal below threshold. | Document as "thesis signal, below threshold." Propose serialization improvements. |
| Arm C ties or loses | Likely Arm B's RAG chunks contain convergence-relevant prose. | Document as null result. Propose serialization or fixture improvements. |
| SD > 0.3 | Rubric instability. | Do not trust the margin. Flag in report. Propose rubric v1.1. |

### Cache and reproducibility

- Arm outputs are cached (content-addressed). Self-consistency re-runs reuse arm outputs; only judge scoring is repeated.
- The thesis run is named `v1-thesis-<commit-sha>` for traceability.
- Scorecard (JSON + markdown) committed to `evals/results/v1-thesis/`. Arm outputs NOT committed (regenerable, large, non-deterministic).

### Braintrust logging

Full run logged to a named Braintrust experiment if `BRAINTRUST_API_KEY` is set. Fallback to local `evals/results/` if unavailable. The experiment URL is referenced in the scorecard README.

## Consequences

- The thesis gate is concrete and preregistered. No post-hoc adjustments.
- Convergence visibility (not curated edges) is the tested capability. This is a more fundamental graph property.
- If the thesis fails, the result is documented and shipped. Follow-up features address the gap rather than rationalizing the result.
- When clinician-reviewed cross-guideline edges return, a follow-up thesis run can measure incremental value on top of convergence.
