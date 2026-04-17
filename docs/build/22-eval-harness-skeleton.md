# 22: Eval harness skeleton (three arms + Braintrust)

**Status**: pending
**Depends on**: 21
**Components touched**: evals / api / docs
**Branch**: `feat/eval-harness-skeleton`

## Context

Stand up the three-arm eval harness end-to-end using v0 statin fixtures only. This is the measurement infrastructure for the entire v1 thesis; landing it on existing fixtures means the content features (F23, F24, F25, F26) immediately have a harness to run against. Also captures v1 baseline numbers: Arm C against the current statin graph alone, before cross-guideline edges exist.

Arms:
- **A** — `PatientContext` only. Vanilla LLM. Tests training knowledge.
- **B** — `PatientContext` + top-k chunks from guideline prose (`docs/reference/guidelines/*.md` and raw guideline text). Flat RAG.
- **C** — `PatientContext` + graph-retrieved context: serialized `EvalTrace` summary + subgraph rooted at matched Recs.

Judge: Claude Opus 4.6, pinned version. Arms: Claude Sonnet 4.6.

## Required reading

- `docs/build/v1-spec.md` — sections on eval harness, three arms, rubric, Braintrust.
- `evals/SPEC.md` — current eval spec; will be extended.
- `evals/INVENTORY.md` — current fixture catalog.
- `api/app/evaluator/` — Arm C consumes evaluator output; understand the trace shape.
- `docs/specs/eval-trace.md` — Arm C serialization derives from this.
- `docs/specs/patient-context.md` — all arms consume this as input.
- Braintrust docs (latest) — confirm free tier limits before committing; free tier must cover ~300 runs during v1 development.

## Scope

- `evals/harness/` — new directory.
  - `evals/harness/runner.py` — orchestrates arm runs per fixture; handles caching.
  - `evals/harness/arms/vanilla.py` — Arm A: PatientContext-only prompt to Sonnet.
  - `evals/harness/arms/flat_rag.py` — Arm B: top-k chunking + retrieval + prompt.
  - `evals/harness/arms/graph_context.py` — Arm C: serializes trace + subgraph, injects, prompts.
  - `evals/harness/judge.py` — rubric-based scoring call to Opus; deterministic structural checks.
  - `evals/harness/serialization.py` — trace → LLM-friendly summary; subgraph → textual context.
  - `evals/harness/braintrust_client.py` — logs datasets, experiments, scores to Braintrust.
  - `evals/harness/cache.py` — content-addressed cache for arm outputs keyed on (fixture, arm, prompt_hash, context_hash, model).
- `evals/rubric.md` — rubric v1: 4 dimensions at 1-5, composite = mean. Judge model + version pinned here.
- `evals/SPEC.md` — amend with harness semantics, caching rules, fixture format extension.
- `evals/fixtures/statins/*/expected-actions.json` — new; one per v0 fixture. Hand-curated next-best-action list with rationale.
- `evals/fixtures/statins/*/arms/` — runtime output directories; gitignored or committed as goldens per rubric-version convention (see design notes).
- `evals/pyproject.toml` — new; harness deps (braintrust-sdk, anthropic, python-dotenv, pydantic).
- `evals/README.md` — new; how to run, how to invalidate cache, how to read scorecards.
- `docs/reference/guidelines/statins.md` — if not already prose-oriented, add a prose rendering suitable for Arm B chunking. Split into sections with stable anchors.
- `scripts/run-eval.sh` — convenience wrapper.

## Constraints

- **Models pinned in `evals/rubric.md`:** arms use `claude-sonnet-4-6`, judge uses `claude-opus-4-6`. Exact version strings. Changing a model forces a re-score under a new rubric version.
- **Temperature 0** for arms; temperature 0 for judge. Determinism for the model call is best-effort (LLMs are not bit-deterministic), but same prompt + same model + temp 0 is close enough for run-to-run comparison.
- **Rubric v1 dimensions (1-5 each):**
  - `completeness` — are all expected actions present?
  - `clinical_appropriateness` — are any recommendations contraindicated or wrong?
  - `prioritization` — is sequencing reasonable (most impactful first)?
  - `integration` — does the output correctly handle cross-guideline interactions? In v1 Phase 1 (single-guideline baseline), this dimension scores 5 by default for all arms since there is nothing to integrate; it activates starting F25/F26.
  - Composite = arithmetic mean. No weighting in v1.
- **Deterministic structural checks run separately** from the LLM judge; results logged alongside rubric scores but not combined into the composite for v1.
- **Per-fixture curated `expected-actions.json`:** schema includes `actions: [{id, label, rationale, source_rec_id?, priority}]`, `contraindications: [...]` (actions that should NOT appear). Format defined in `evals/SPEC.md`.
- **Cache invalidation:** key on (fixture path, arm id, context hash, prompt hash, model version string). When any component changes, cache entry invalidates. Store cache in `evals/fixtures/<guideline>/<id>/arms/<arm>/` with a `meta.json` alongside `output.json` capturing the hash inputs.
- **Braintrust integration is optional at runtime:** if `BRAINTRUST_API_KEY` is unset, harness runs locally and logs to `evals/results/<timestamp>/`. If the key is set, also log to Braintrust. This keeps the fallback path alive (v1 spec risk mitigation).
- **No parallelism in v1.** Sequential runs. Easier to debug; latency is not a concern at 18 fixtures.
- **Arm C serialization format** defined in `evals/harness/serialization.py` with a frozen output shape documented in `evals/SPEC.md`. Shape: `{trace_summary: {matched_recs: [...], preemption_events: [...], modifier_events: [...]}, subgraph: {nodes: [...], edges: [...], rendered_prose: "..."}}`. The `rendered_prose` field is a natural-language rendering so the LLM doesn't have to reason over JSON alone.
- **Arm B top-k:** start at k=5 chunks, chunk size 500 tokens with 50-token overlap. Embeddings: `text-embedding-3-small` via OpenAI API, or `voyage-2` via Voyage. Pick one in this feature and document it in `evals/SPEC.md`. (Recommendation: `text-embedding-3-small` for cost; revisit in F27 if Arm B is underperforming because of retrieval quality, not graph value.)

## Verification targets

- `cd evals && uv run python -m harness.runner --fixture statins/case-01 --arm a` — exits 0, writes `evals/fixtures/statins/case-01/arms/a/output.json`.
- Same for arms b and c.
- `uv run python -m harness.runner --all` runs all 5 v0 fixtures × 3 arms = 15 runs, scores each with the judge, writes a scorecard.
- Re-running with no changes hits cache for every run (0 LLM calls).
- Modifying a prompt in one arm invalidates only that arm's cache for all fixtures.
- `BRAINTRUST_API_KEY` set: Braintrust shows a new experiment with 15 entries and 4 scores per entry.
- `BRAINTRUST_API_KEY` unset: harness still runs; results land in `evals/results/<timestamp>/`.
- Baseline numbers captured: Arm A, Arm B, Arm C composite scores on v0 fixtures. These are the "single-guideline baseline" reference that F27 compares against.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Unit tests for cache key hashing and invalidation.
- Integration test: run harness against one fixture, assert scorecard shape and content.
- `expected-actions.json` hand-curated for all 5 v0 fixtures; reviewed by human before merge.
- Rubric pinned in `evals/rubric.md` with model version strings.
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output; include screenshot of Braintrust experiment if free tier active.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- ACC/AHA Cholesterol content (F23) and KDIGO content (F24).
- Preemption resolution (F25) and modifier handling (F26).
- Full thesis evaluation run on 18 fixtures (F27).
- UI for viewing eval results.
- Parallel execution.
- Judge self-consistency checks (running the judge N times and averaging). Save for F27 if needed.

## Design notes (not blocking, worth review)

- **Goldens for arm outputs:** committing LLM outputs as goldens is tempting but fragile. Recommendation: do not commit `arms/*/output.json` to git. Treat them as regenerable. Commit `expected-actions.json` (human-curated ground truth) and the final scorecard summary only. This keeps the repo small and avoids diff noise from LLM non-determinism.
- **Arm B chunking source:** USPSTF statin guideline prose doesn't exist in `docs/reference/guidelines/` yet in a chunking-friendly form. This feature adds a prose rendering. For F23 (ACC/AHA) and F24 (KDIGO), the guideline authors must produce a parallel prose doc for Arm B.
- **Judge bias mitigations:** pinning a different model for judge vs. arms covers self-preference. If the judge shows signs of favoring any arm consistently (e.g., always scores Arm A highest because it's "clean"), add a blinding step in F27 where arm labels are randomized in the judge prompt.
- **Contradiction between arms:** what if Arm A says SGLT2 and Arm C says SGLT2 too? Both get credit. Scoring is absolute, not relative. Relative analysis happens at the scorecard level.
- **Braintrust cost watch:** free tier at ~300 runs is fine, but iterating on prompts during F23-F27 can easily 10x that. If development runs start costing, gate Braintrust logging behind an env flag and log only scored runs there.
