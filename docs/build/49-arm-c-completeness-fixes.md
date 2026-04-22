# 49: Arm C completeness fixes

**Status**: pending
**Depends on**: 47
**Components touched**: evals / graph / docs
**Branch**: `feat/arm-c-completeness-fixes`

## Context

F47's combined run showed Arm C Completeness stuck at 3.40 on multi-guideline fixtures — flat since F44 and the weakest dimension. Detailed fixture inspection (cross-domain cases 03, 06, 08, 10) revealed three distinct root causes:

1. **Satisfied strategies not surfaced as "continue" actions.** The graph correctly marks strategies as `up_to_date` (e.g., ACEi/ARB in case-08, ACEi in case-10), but the Arm C prompt doesn't instruct the LLM to recommend continuing them. The LLM sees "satisfied" and stays silent. Expected actions include "Continue ARB therapy" / "Continue ACEi" — these are clinically important maintenance actions.

2. **Preemption/modifier reasoning not echoed in output.** The graph provides preemption and modifier prose in the context (e.g., "ACC/AHA preempts USPSTF" in case-06, "KDIGO modifies intensity to moderate" in case-08). The LLM acts on it (recommends the right drug) but doesn't articulate the *reasoning* about guideline hierarchy. The judge penalizes this because the expected actions specify the reasoning, not just the action.

3. **Fixture expected-actions bug (case-03 SGLT2).** Case-03 expects "Initiate SGLT2 inhibitor" but the patient has ACR 180 mg/g. KDIGO requires ACR ≥ 200 for non-diabetic patients. The graph correctly does not fire the SGLT2 rec. The expected actions are wrong — this inflates the apparent Completeness gap.

Issues 1 and 2 are shared with Arm B (both score 3 on the same fixtures), but Arm C has the information to do better — the graph provides the satisfied-strategy status and the interaction prose. The serialization just doesn't leverage it.

## Required reading

- `evals/harness/arms/graph_context.py` — Arm C prompt template and context assembly
- `evals/harness/serialization.py` — convergence and trace serialization
- `evals/rubric.md` — completeness scoring criteria
- `evals/fixtures/cross-domain/case-03/expected-actions.json` — SGLT2 bug
- `evals/fixtures/cross-domain/case-08/expected-actions.json` — continue-ARB pattern
- `evals/fixtures/cross-domain/case-10/expected-actions.json` — continue-ACEi pattern
- `docs/specs/eval-trace.md` — trace event types (for satisfied strategy status)

## Scope

### 1. Serialization: surface satisfied strategies as "continue" actions

- `evals/harness/serialization.py` — when building the Arm C context, include a "Currently Satisfied" section listing strategies with status `up_to_date` and a clear instruction: "The patient is already receiving these therapies. Recommend continuing them."
- `evals/harness/arms/graph_context.py` — update the prompt template to include the satisfied-strategies section and instruct the LLM: "For therapies the patient is already receiving that align with guideline recommendations, explicitly recommend continuation."

### 2. Serialization: make interaction reasoning more prominent

- `evals/harness/arms/graph_context.py` — restructure the cross-guideline interactions section to be more directive. Instead of just providing prose, instruct the LLM: "When multiple guidelines apply, explicitly state which guideline takes precedence and why."
- The preemption and modifier prose already exists in `trace_summary`; the change is in how prominently it's surfaced and what the LLM is told to do with it.

### 3. Fix case-03 expected actions

- `evals/fixtures/cross-domain/case-03/expected-actions.json` — remove the SGLT2 action. ACR 180 < 200 threshold for non-diabetic SGLT2 eligibility per KDIGO 3.8.1. Add a contraindication entry: "Do not recommend SGLT2 inhibitor (ACR 180 below non-diabetic threshold of 200)."

### 4. Update build-status

- `docs/reference/build-status.md` — add row for F49.

## Constraints

- **Do not change the rubric.** Same v1.1 rubric, same judge model, same arm model.
- **Do not change Arm A or Arm B.** Only Arm C's serialization and prompt change.
- **Do not add or remove fixtures** beyond fixing the case-03 expected actions bug.
- **Determinism preserved.** Same `PatientContext` + same graph + same serialization = same prompt. No randomness introduced.

## Verification targets

- `cd evals && uv run python -m harness --arm c --fixture cross-domain/case-08 --run v2-f49-test` — Arm C output includes "Continue ARB/losartan" as an explicit action.
- `cd evals && uv run python -m harness --arm c --fixture cross-domain/case-10 --run v2-f49-test` — Arm C output includes "Continue ACEi" as an explicit action.
- `cd evals && uv run python -m harness --arm c --fixture cross-domain/case-06 --run v2-f49-test` — Arm C output explicitly states ACC/AHA preemption of USPSTF.
- Case-03 expected-actions.json no longer lists SGLT2 as an expected action; contraindication added.
- Existing evals tests pass (`cd evals && uv run pytest` if applicable).

## Definition of done

- Serialization changes committed and tested on the 4 target fixtures.
- Case-03 expected actions fixed.
- `docs/reference/build-status.md` updated.
- PR opened with before/after examples showing the changed LLM output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Full harness re-run (that's a separate thesis run feature after this ships).
- Arm B improvements (Arm B doesn't have satisfied-strategy or interaction data to leverage).
- Rubric changes or new scoring dimensions.
- New fixtures beyond the case-03 fix.
- Changes to the graph seeds or evaluator API (the graph already produces the right trace data; this is purely a serialization/prompt change).
- Structural check label matching improvements (the structural checks are informational, not gating; fix separately if desired).
