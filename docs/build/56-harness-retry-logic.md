# 56: Judge retry logic + clean re-run

**Status**: pending
**Depends on**: 55
**Components touched**: evals / docs
**Branch**: `feat/judge-retry-logic`

## Context

F55's Phase 2 thesis run appeared to have 15 missing fixture/arm entries. Post-run diagnosis revealed two distinct issues:

**1. Stale data in Braintrust fetch (cosmetic, not data loss).** `fetch_from_braintrust()` via `init_experiment(open=True)` returns rows from prior experiment versions of the same name. A v2-phase2-arm-a experiment has 96 rows: 32 from the current run (scored), 32 from a prior run (output only, no scores), and 32 from an even older run (no fixture_id). The `if not scores: continue` filter correctly drops stale rows, but the N counts in the scorecard were misleading — they reflected judge failures, not task failures.

**2. Judge API 500 errors (real data loss).** The `clinical_scorer` function calls Anthropic's API (claude-opus-4-20250514) with no retry logic. When the API returns a 500 during concurrent scoring, the scorer throws, Braintrust records the row without scores, and `fetch_from_braintrust` drops it. For Arm A, exactly 3 fixtures failed: `cholesterol/case-03`, `cross-domain/case-05`, `cross-domain/case-07` — all judge 500s, not task failures. The arm output exists for all 32 fixtures.

**Actual data loss: ~9 entries across 3 arms (~9.4%), not 15.** All failures are in the judge, not the arm task functions.

## Required reading

- `evals/harness/judge.py` — `score()` and `clinical_scorer()` functions. The Anthropic API call at line 210 has no retry.
- `evals/harness/scorecard.py` — `fetch_from_braintrust()` pulls stale rows from prior experiment versions.
- `evals/harness/config.py` — config constants.
- `evals/harness/arms/graph_context.py` — Arm C task fn (`httpx.Client` timeout is 30s, marginal for 4-guideline patients).

## Scope

- `evals/harness/judge.py` — Add retry with exponential backoff to the Anthropic API call in `score()`. 3 retries, 5/10/20s delays. Log each retry to stderr.
- `evals/harness/scorecard.py` — Fix `fetch_from_braintrust()` to filter out stale rows. Either filter by `experiment.id` or only include rows that have scores (current behavior works but produces misleading diagnostics). Add a `--verbose` mode that reports total rows fetched vs scored vs dropped.
- `evals/harness/config.py` — Add `JUDGE_MAX_RETRIES` and `JUDGE_RETRY_DELAY_SECONDS` constants.
- `evals/harness/arms/graph_context.py` — Increase `httpx.Client` timeout from 30s to 60s.
- `evals/results/v2-phase2-r2/` — NEW directory: clean re-run with judge retry in place.
  - `scorecard.md`
  - `scorecard.json`
  - `README.md` — data completeness verification, comparison to F55, updated thesis gate assessment with complete data.
- `docs/reference/build-status.md` — update row for F56.

## Constraints

- **Retry belongs in `judge.py`, not the harness runner.** The Braintrust `Eval()` framework calls the scorer; we can't retry from outside. The retry wraps the `client.messages.create()` call inside `score()`.
- **Only retry on transient errors.** Retry on HTTP 500, 502, 503, 529 (overloaded). Do not retry on 400 (bad request) or 401 (auth). Use the Anthropic SDK's error types to distinguish.
- **Exponential backoff.** Delay = `JUDGE_RETRY_DELAY_SECONDS * 2^attempt`.
- **No rubric changes, no arm prompt changes, no fixture changes.** Infrastructure fix + clean re-run.
- **The re-run uses a fresh experiment name** (`v2-phase2-r2`) to avoid stale-row contamination.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-phase2-r2` completes.
- Braintrust shows 3 experiments (`v2-phase2-r2-arm-{a,b,c}`) with 32 scored entries each.
- `cd evals && uv run python -m harness --scorecard --run v2-phase2-r2 --output-dir results/v2-phase2-r2` produces scorecard.
- Scorecard shows N=16 for all arms on multi-guideline subset, N=16 for single-guideline subset. **Zero missing entries.**
- README includes the corrected Phase 1 → Phase 2 comparison with complete data.
- Thesis gate assessment stated with full-data margin.

## Definition of done

- Judge retry logic implemented.
- `fetch_from_braintrust` stale-row issue documented (and optionally filtered).
- Full harness re-run completed with 32/32 scored entries per arm.
- Scorecard committed to `evals/results/v2-phase2-r2/`.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Arm prompt or serialization changes (F57, F58).
- Rubric or judge model changes.
- Retry logic in the arm task functions (task functions succeeded for all 32 fixtures in F55; the failures were all in the judge).
