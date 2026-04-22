# 50: Arm C scoring leverage (integration schema + negative evidence + completeness licensing)

**Status**: pending
**Depends on**: 49
**Components touched**: evals / docs
**Branch**: `feat/arm-c-scoring-leverage`

## Context

F47's combined run shows C-B margin at +0.175 (need ≥0.5). Per-fixture analysis of the v2-phase1 scorecard reveals three systemic patterns explaining the gap:

1. **Integration underscoring (6 of 10 multi-guideline cases ≤ 3).** The graph provides preemption and modifier data that RAG cannot access, yet Arm C's flat JSON action list buries the cross-guideline reasoning inside individual action rationale strings. The judge must *infer* integration handling rather than directly observing it. Cases 04, 05, 06, 09, 10 all have Integration ≤ 3 despite the trace containing explicit cross-guideline edge data.

2. **Negative evidence discarded.** Cases 09 and 10 are tied or near-tied with B (3.0 / 3.0 and 3.0 / 2.75). Both are designed to test whether the system correctly attributes what *didn't* fire — USPSTF evaluated but ineligible at ASCVD 6.8% (case-10), USPSTF Grade C preempted and shouldn't be framed as the statin rationale (case-09). The trace contains this information (guidelines entered → zero recs emitted, or recs preempted), but the serialization only surfaces what matched. RAG fundamentally cannot replicate negative evidence — this is the graph's unique structural advantage and we're throwing it away.

3. **Graph anchoring suppresses non-graph actions.** The graph covers guideline-specific pharmacotherapy but not lifestyle interventions (smoking cessation, diet, exercise) or conditional follow-ups (ezetimibe add-on if LDL remains ≥100). Arm C's prompt anchors the LLM so strongly to graph output that it omits clinically relevant actions the graph doesn't encode. Case-07 (C completeness=4 vs B=5) and case-09 (smoking cessation missing from both arms, but C has the data to infer it from social_history) are direct consequences.

These three changes target different dimensions (Integration, Completeness) across different fixture subsets with minimal overlap. Estimated margin improvement: +0.225 to +0.325, which combined with the current +0.175 puts projected margin at +0.400 to +0.500.

## Required reading

- `evals/results/v2-phase1/scorecard.json` — per-fixture, per-arm, per-dimension scores
- `evals/harness/arms/graph_context.py` — Arm C prompt template (includes F49 changes)
- `evals/harness/serialization.py` — trace-to-context serialization (includes F49 changes)
- `evals/harness/config.py` — shared system prompt with output JSON schema
- `evals/harness/judge.py` — judge prompt and integration scoring criteria
- `evals/rubric.md` — rubric v1.1 dimension definitions
- `docs/specs/eval-trace.md` — trace event types (guideline_entered, guideline_exited, exit_condition_triggered, recommendation_emitted)
- `evals/fixtures/cross-domain/case-09/expected-actions.json` — convergence + preemption case
- `evals/fixtures/cross-domain/case-10/expected-actions.json` — KDIGO bias probe

## Scope

### 1. Arm C output schema: explicit cross-guideline resolutions section

The shared `SYSTEM_PROMPT` in `config.py` defines the output JSON schema used by all three arms. Do **not** modify `config.py`. Instead, override the output format instruction in the Arm C prompt template (`graph_context.py`) to request an extended schema:

- `evals/harness/arms/graph_context.py` — replace the current "Respond with a JSON object containing your recommended actions" with a structured output instruction that requests:
  ```json
  {
    "actions": [...],
    "cross_guideline_resolutions": [
      {
        "type": "preemption" | "modification" | "convergence",
        "guidelines_involved": ["ACC/AHA 2018", "USPSTF 2022"],
        "resolution": "ACC/AHA preempts USPSTF Grade B because...",
        "impact_on_actions": "Statin recommendation follows ACC/AHA, not USPSTF"
      }
    ],
    "guidelines_without_recommendations": [
      {
        "guideline": "USPSTF 2022 Statin",
        "reason": "ASCVD 6.8% below 7.5% Grade C threshold — no rec eligible"
      }
    ],
    "reasoning": "..."
  }
  ```
  The `cross_guideline_resolutions` section should only be requested when the trace contains preemption, modifier, or convergence events. For single-guideline evaluations with no interactions, omit it to avoid hallucinated resolutions.
  The `guidelines_without_recommendations` section should only be requested when the serialization includes negative evidence (see scope item 2).

### 2. Negative evidence serialization: guidelines evaluated without recommendations

- `evals/harness/serialization.py` — add `serialize_negative_evidence(trace)` function:
  - Walk the trace events. For each `guideline_entered` / `guideline_exited` pair, check whether any `recommendation_emitted` events exist for that guideline_id.
  - If a guideline was entered but zero recs were emitted (all exited or ineligible), capture: `guideline_id`, `guideline_title`, and the exit reasons (from `exit_condition_triggered` events for that guideline) or "no eligible recommendations" if no exits either.
  - If a guideline had recs but all were preempted (check `preemption_resolved` events), capture: `guideline_id`, `guideline_title`, preempted rec IDs, preempting guideline.
  - Return a list of `{"guideline_id", "guideline_label", "reason"}` dicts.
  - Wire into `build_arm_c_context()` under key `negative_evidence`.

- `evals/harness/arms/graph_context.py` — add a "Guidelines Evaluated Without Recommendations" section to the prompt template:
  - Only render when `negative_evidence` is non-empty.
  - Format: "The following guidelines were evaluated for this patient but produced no applicable recommendations:" followed by guideline name + reason.
  - Add instruction: "When a guideline was evaluated and did not fire, this is clinically significant. Do not attribute actions to guidelines that did not produce recommendations for this patient."

### 3. Completeness licensing: clinical context beyond graph

- `evals/harness/arms/graph_context.py` — add a short paragraph to the Instructions block:
  - "The knowledge graph covers guideline-specific pharmacotherapy recommendations. For clinically relevant actions not encoded in the graph — including lifestyle modifications (smoking cessation, diet, exercise), monitoring follow-ups conditional on treatment response, and blood pressure optimization — apply your clinical knowledge based on the patient context. Do not limit your recommendations to only what the graph covers."
  - This goes in the existing Instructions block (added by F49), not as a separate section.

### 4. Update build-status

- `docs/reference/build-status.md` — add row for F50.

## Constraints

- **Do not modify `evals/harness/config.py`.** The shared system prompt and output schema stay unchanged. Arm C's extended output format is injected via its own prompt template only.
- **Do not modify `evals/harness/judge.py` or `evals/rubric.md`.** Same v1.1 rubric, same judge model, same judge prompt. The improvement must come from giving the LLM better context and letting it produce output the judge can already score higher under existing criteria.
- **Do not modify Arm A or Arm B.** Only Arm C's serialization and prompt change.
- **Do not add or remove fixtures.** Same 22 fixtures, same expected-actions.
- **Determinism preserved.** Same `PatientContext` + same graph + same serialization = same prompt. No randomness introduced.
- **Backward compatibility.** The `parsed` output from Arm C must still contain an `actions` array with the same shape as before. The new `cross_guideline_resolutions` and `guidelines_without_recommendations` fields are additive. The judge only sees `parsed` (which is the full JSON), so the new sections will be visible to it.

## Verification targets

- `cd evals && uv run pytest tests/test_serialization.py -v` — all tests pass including new negative-evidence tests.
- Dry-run the Arm C prompt builder against a multi-guideline trace fixture (e.g., case-08 or case-10) and verify:
  - The "Currently Satisfied Strategies" section renders (from F49).
  - The "Guidelines Evaluated Without Recommendations" section renders when applicable.
  - The output format instruction includes `cross_guideline_resolutions` and `guidelines_without_recommendations`.
  - The completeness licensing paragraph is present in the Instructions block.
- Dry-run the Arm C prompt builder against a single-guideline trace fixture and verify:
  - The `cross_guideline_resolutions` section is NOT requested in the output format.
  - The "Guidelines Evaluated Without Recommendations" section does NOT render.
- `serialize_negative_evidence()` unit tests:
  - Trace with a guideline that entered but had zero recs emitted → returns one entry.
  - Trace where all recs from a guideline were preempted → returns one entry citing the preempting guideline.
  - Trace where all guidelines produced recs → returns empty list.
  - Single-guideline trace → returns empty list (USPSTF always fires something or exits).

## Definition of done

- All scope files modified and tested.
- All verification targets pass locally.
- Unit tests for `serialize_negative_evidence` written and passing.
- Existing serialization tests still pass.
- `docs/reference/build-status.md` updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- Full harness re-run (that's a separate thesis run feature after this ships).
- Rubric changes, judge prompt changes, or judge model changes.
- Arm A or Arm B modifications.
- New fixtures or expected-actions changes.
- Changes to the graph seeds, evaluator API, or Neo4j schema.
- Modifying the shared system prompt in `config.py`.
- Arm C output parsing changes in `graph_context.py:run()` — the existing JSON-extraction logic already handles additional fields gracefully.
