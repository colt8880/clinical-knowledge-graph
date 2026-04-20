# 27: Full harness run and thesis test

**Status**: pending
**Depends on**: 22, 23, 24, 33
**Components touched**: evals / docs
**Branch**: `feat/harness-thesis-test`

## Context

The capstone v1 feature. Runs the full three-arm harness across all fixtures, generates the scorecard, and evaluates the thesis against the preregistered margin: **Arm C beats Arm B on the multi-guideline fixture subset by ≥ 0.5 composite points**.

### Thesis pivot (2026-04-20)

The original thesis measured Arm C's advantage via cross-guideline edges (PREEMPTED_BY, MODIFIES). Those edges were removed pending clinician review after modeling errors were found (see `docs/ISSUES.md`). The thesis now measures **convergence visibility**: the graph's ability to show that multiple guidelines independently recommend the same therapeutic actions via shared clinical entities.

The hypothesis: Arm C's explicit convergence summary — "three guidelines independently recommend moderate-intensity statin for this patient, via these pathways" — anchors the LLM to multi-source clinical agreement, producing better Integration scores than Arm B's disconnected prose chunks. Flat RAG retrieves guideline text but cannot structurally identify that separate guidelines target the same medications.

This pivot does not weaken the thesis. Convergence visibility is a more fundamental graph capability than edge-based conflict resolution. If the graph can't demonstrate value through convergence, adding edges won't fix it.

Passing this gate is the signal that v1 has proven what it set out to prove. Failing it is also a result: it means the serialization, the rubric, or the thesis itself needs work. Do not rationalize a failed result by adding more guidelines.

## Required reading

- `docs/build/v1-spec.md` — success criterion #4 and the preregistered margin.
- `evals/rubric.md` — rubric v1; pinned judge model and dimensions.
- `docs/build/22-eval-harness-skeleton.md` — harness semantics.
- `docs/build/33-arm-c-convergence-serialization.md` — the convergence summary Arm C now includes.
- All fixture READMEs.
- `docs/decisions/0020-three-arm-eval-methodology.md` — NEW ADR; documents the methodology, margin, judge pinning, what counts as pass/fail, what to do on failure. MUST be merged before this feature's PR.

## Scope

- `docs/decisions/0020-three-arm-eval-methodology.md` — NEW ADR. Documents the convergence-based thesis methodology, margin, judge pinning, and failure handling.
- `evals/harness/scorecard.py` — new; aggregates per-fixture scores into per-arm totals with breakdowns by dimension and fixture subset (single-guideline vs. multi-guideline).
- `evals/harness/report.py` — new; emits a markdown scorecard report and a JSON artifact.
- `evals/results/v1-thesis/` — new directory; commits the final scorecard JSON and markdown for historical record. Arm outputs NOT committed (consistent with F22 design note).
- `evals/results/v1-thesis/scorecard.md` — human-readable scorecard.
- `evals/results/v1-thesis/scorecard.json` — machine-readable scorecard.
- `evals/results/v1-thesis/README.md` — prose summary of the thesis run: setup, results, interpretation, failure analysis if applicable.
- `docs/reference/build-status.md` — v1 completion row marking thesis gate pass/fail.
- Braintrust experiment: `v1-thesis-<commit-sha>` logged, referenced by URL in the scorecard README.

## Fixture set

| Subset | Fixtures | Count | Purpose |
|--------|----------|-------|---------|
| Single-guideline (statins) | `evals/fixtures/statins/case-01` through `case-05` | 5 | Baseline — Arm C should be comparable to Arm B |
| Single-guideline (cholesterol) | `evals/fixtures/cholesterol/case-01` through `case-04` | 4 | Baseline |
| Single-guideline (KDIGO) | `evals/fixtures/kdigo/case-01` through `case-03` | 3 | Baseline |
| Multi-guideline | `evals/fixtures/cross-domain/case-01` through `case-04` | 4 | **Thesis differentiator** — Arm C should outperform Arm B via convergence visibility |
| **Total** | | **16** | |

The multi-guideline fixtures exercise patients matching 2-3 guidelines simultaneously. The graph's convergence summary (F33) gives Arm C explicit knowledge of which guidelines agree on the same therapeutic action. Arm B gets disconnected prose chunks.

## Constraints

- **Preregistered margin:** Arm C mean composite on the multi-guideline fixture subset (4 fixtures) must exceed Arm B's by ≥ 0.5 points on the 1-5 scale. This is the thesis gate. Defined in ADR 0020; do not change during this feature.
- **Integration dimension is the primary differentiator.** On multi-guideline fixtures, Arm C's convergence summary should most strongly improve Integration scores. Completeness, Clinical Appropriateness, and Prioritization may be similar across arms for well-constructed fixtures. Report per-dimension breakdowns.
- **Single-guideline subset:** Arm C on single-guideline fixtures (12 fixtures) should be roughly comparable to Arm B — convergence doesn't apply when only one guideline fires. Record the numbers for transparency but do not gate on them.
- **No rubric tweaks in this feature.** Rubric is frozen as of F22. If the run reveals the rubric is broken, STOP and open a separate rubric-v1.1 feature.
- **No prompt tweaks in this feature.** Prompts are frozen per-arm as of F22 + F33; changes go in a separate feature.
- **Self-consistency check:** run the judge 3 times on the full set (3 × 16 × 3 arms = 144 scoring calls) and report mean + standard deviation of the composite. If SD > 0.3 on any arm/subset, flag rubric instability in the report. Documented in ADR 0020.
- **Failure handling:** if Arm C does not beat Arm B by the margin, the scorecard report documents:
  1. Per-dimension gap analysis (which of the 4 dimensions is underperforming).
  2. Per-fixture breakdown (which specific cases are failing).
  3. Hypotheses: serialization gap (convergence summary not informative enough), retrieval gap (Arm B chunks are surprisingly good), fixture construction gap (cases don't actually exercise convergence), or genuine null result.
  4. Recommended next feature(s) to address the gap.
  Ship the report regardless. Do not merge this feature with a silent failure.
- **Braintrust:** full run logged to a named experiment. Fallback to jsonl if Braintrust is unavailable.

## Verification targets

- ADR 0020 merged before this PR opens.
- `cd evals && uv run python -m harness.runner --all` completes across all 16 fixtures × 3 arms with no errors.
- `uv run python -m harness.scorecard --run v1-thesis` produces both `scorecard.md` and `scorecard.json`.
- Scorecard JSON conforms to documented shape (schema in `evals/SPEC.md`).
- Self-consistency SDs reported.
- Braintrust experiment visible with entries per arm per judge run.
- Scorecard explicitly states "THESIS GATE: PASS" or "THESIS GATE: FAIL" with evidence.

## Definition of done

- ADR 0020 written, reviewed, merged.
- Full harness run completed.
- Scorecard committed.
- Self-consistency numbers reported.
- Result (pass or fail) documented clearly in `evals/results/v1-thesis/README.md`.
- If pass: v1 is thesis-complete.
- If fail: follow-up feature scoped in `docs/ISSUES.md` with clear remediation plan.
- `docs/reference/build-status.md` updated with thesis result.
- PR opened with Scope / Manual Test Steps / Manual Test Output (the Output IS the scorecard).
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Cross-guideline edges (PREEMPTED_BY, MODIFIES). Blocked on clinician review. When clinician-reviewed edges return, a follow-up thesis run can measure the incremental value of edges on top of convergence.
- UI changes (F30).
- Rubric iteration. Separate feature if needed.
- Adding fixtures. Separate feature if needed.
- Cross-vendor arm validation (running arms with GPT models too). v2.
- Running the harness in CI. v2 or a follow-up chore feature.

## Design notes (not blocking, worth review)

- **Why convergence is a stronger first thesis than edges.** Edges encode curated conflict resolution — a human (or validated LLM) decided "ACC/AHA preempts USPSTF." That's valuable but it's injected knowledge, not structural reasoning. Convergence is emergent from the graph structure: the fact that three independent guidelines point at the same medication node is a structural property no single guideline document contains. If the graph can't demonstrate value through this structural property, adding curated edges on top won't produce a genuine thesis proof.
- **What "≥ 0.5 margin" means concretely:** Arm B mean composite on multi-guideline fixtures is 3.2 (hypothetical); Arm C must be ≥ 3.7 to pass the gate.
- **Interpreting a narrow Arm C win (0.1-0.4).** Not a pass, but not null. Document as "thesis signal, below threshold" and propose serialization improvements.
- **Interpreting an Arm C LOSS.** Likely cause: Arm B's RAG chunks happen to contain convergence-relevant prose (e.g., "both USPSTF and ACC/AHA recommend..."). This would mean the flat guideline documents already contain the convergence signal and the graph's structural representation doesn't add enough. The remedy is better serialization, not more edges.
- **Why 16 fixtures not 18.** The original spec counted 2 cross-domain fixtures from F25 and 4 from F26 = 6. With edges removed, the cross-domain fixtures don't exercise preemption/modification but still exercise multi-guideline convergence. The 4 cross-domain fixtures remain; the 2 that were specifically PREEMPTED_BY-only (F25) are redundant with the 4 that cover the same patients from multiple angles.
