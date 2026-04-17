# 27: Full harness run and thesis test

**Status**: pending
**Depends on**: 22, 23, 24, 25, 26
**Components touched**: evals / docs
**Branch**: `feat/harness-thesis-test`

## Context

The capstone v1 feature. Runs the full three-arm harness across all 18 fixtures (5 statins + 4 cholesterol + 3 KDIGO + 2 cross-domain from F25 + 4 cross-domain from F26), generates the scorecard, and evaluates the thesis against the preregistered margin: **Arm C beats Arm B on the cross-domain fixture subset by ≥ 0.5 composite points**.

Passing this gate is the signal that v1 has proven what it set out to prove. Failing it is also a result: it means the graph-context serialization, the rubric, or the thesis itself needs work. Do not rationalize a failed result by adding more guidelines.

## Required reading

- `docs/build/v1-spec.md` — success criterion #4 and the preregistered margin.
- `evals/rubric.md` — rubric v1; pinned judge model and dimensions.
- `docs/build/22-eval-harness-skeleton.md` — harness semantics.
- All fixture READMEs.
- `docs/decisions/0020-three-arm-eval-methodology.md` — NEW ADR; documents the methodology, margin, judge pinning, what counts as pass/fail, what to do on failure. MUST be merged before this feature's PR.

## Scope

- `docs/decisions/0020-three-arm-eval-methodology.md` — NEW ADR.
- `evals/harness/scorecard.py` — new; aggregates per-fixture scores into per-arm totals with breakdowns by dimension and fixture subset (single-guideline vs. cross-domain).
- `evals/harness/report.py` — new; emits a markdown scorecard report and a JSON artifact.
- `evals/results/v1-thesis/` — new directory; commits the final scorecard JSON and markdown for historical record. Arm outputs NOT committed (consistent with F22 design note).
- `evals/results/v1-thesis/scorecard.md` — human-readable scorecard.
- `evals/results/v1-thesis/scorecard.json` — machine-readable scorecard.
- `evals/results/v1-thesis/README.md` — prose summary of the thesis run: setup, results, interpretation, failure analysis if applicable.
- `docs/reference/build-status.md` — v1 completion row marking thesis gate pass/fail.
- Braintrust experiment: `v1-thesis-<commit-sha>` logged, referenced by URL in the scorecard README.

## Constraints

- **Preregistered margin:** Arm C mean composite on the cross-domain fixture subset (6 fixtures: 2 from F25 + 4 from F26) must exceed Arm B's by ≥ 0.5 points on the 1-5 scale. This is the thesis gate. Defined in ADR 0020; do not change during this feature.
- **Single-guideline subset:** Arm C on single-guideline fixtures (12 fixtures: 5 statins + 4 cholesterol + 3 KDIGO) should be roughly comparable to Arm B — the graph's value shines on cross-domain cases, not single-domain. Record the single-guideline numbers for transparency but do not gate on them.
- **No rubric tweaks in this feature.** Rubric is frozen as of F22. If the run reveals the rubric is broken (e.g., judge consistently gives max scores across all arms), STOP. Open a separate rubric-v1.1 feature; do not mix methodology changes into the thesis run.
- **No prompt tweaks in this feature.** Same as rubric. Prompts are frozen per-arm as of F22; changes go in a separate feature.
- **Self-consistency check:** run the judge 3 times on the full set (3 × 18 × 3 arms = 162 scoring calls) and report mean + standard deviation of the composite. If SD > 0.3 on any arm/subset, flag rubric instability in the report and recommend remediation before claiming thesis pass/fail. This is the only methodology addition allowed in this feature (documented in ADR 0020).
- **Failure handling:** if Arm C does not beat Arm B by the margin, the scorecard report documents:
  1. Per-dimension gap analysis (which of the 4 dimensions is underperforming).
  2. Per-fixture breakdown (which specific cases are failing).
  3. Hypotheses: serialization gap, retrieval gap, fixture construction gap, or genuine null result.
  4. Recommended next feature(s) to address the gap.
  Ship the report regardless. Do not merge this feature with a silent failure.
- **Braintrust:** full run logged to a named experiment, URL captured in the report. Free-tier event count estimate: 18 fixtures × 3 arms × 3 judge calls + 18 × 3 arm generations = 216 LLM calls + metadata. Well under free tier limits.

## Verification targets

- ADR 0020 merged before this PR opens.
- `cd evals && uv run python -m harness.runner --all` completes across all 18 fixtures × 3 arms with no errors.
- `uv run python -m harness.scorecard --run v1-thesis` produces both `scorecard.md` and `scorecard.json`.
- Scorecard JSON conforms to documented shape (schema in `evals/SPEC.md`).
- Self-consistency SDs reported.
- Braintrust experiment visible in UI with 18 entries per arm per judge run.
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

- UI changes (F28-F30).
- Rubric iteration. Separate feature if needed.
- Adding fixtures. Separate feature if needed.
- Cross-vendor arm validation (running arms with GPT models too). v2.
- Running the harness in CI. v2 or a follow-up chore feature.
- Public-facing demo or write-up. Separate work stream.

## Design notes (not blocking, worth review)

- **What "≥ 0.5 margin" means concretely:** Arm B mean composite on cross-domain fixtures is 3.2 (hypothetical); Arm C must be ≥ 3.7 to pass the gate. The 0.5 floor was chosen because it's meaningfully larger than likely judge noise (SD 0.1-0.2 per dimension) without being so large it's only achievable on perfect Arm C runs.
- **Interpreting a narrow Arm C win (0.1-0.4).** This is not a pass, but it's also not a null result. Document it as "thesis signal, below threshold" and propose a v1.1 focused on improving the weakest dimension.
- **Interpreting an Arm C LOSS.** If Arm C underperforms Arm B, the likely cause is Arm C serialization quality. Flat RAG with good prose chunks can beat a poorly-serialized graph context. This would motivate serialization work, not schema work. The failure-handling section of the report makes this call explicitly.
- **Why the judge runs 3x:** LLM judges have real run-to-run variance even at temp 0. Reporting SD is cheap and surfaces rubric instability. If SD is high, the thesis pass/fail is not reliable and rubric work comes first.
- **Why commit the scorecard.** Historical record. Future rubric changes can be compared against this baseline. The scorecard is the concrete artifact v1 was built to produce.
- **What if Braintrust free tier rate-limits mid-run?** Fallback logging to jsonl is already implemented in F22. Scorecard generator reads from local jsonl if Braintrust is unavailable. This feature should not add a hard dependency on Braintrust being up.
