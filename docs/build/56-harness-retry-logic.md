# 56: Harness retry logic

**Status**: pending
**Depends on**: 55
**Components touched**: evals / docs
**Branch**: `feat/harness-retry-logic`

## Context

F55's Phase 2 thesis run had 15 missing fixture/arm entries out of 96 expected (15.6%). The missingness was uneven across arms (Arm C lost 7, Arm B lost 5, Arm A lost 3), making aggregate comparisons unreliable because each arm's mean was computed over a different fixture set. Root cause: the Braintrust `Eval()` runner silently drops entries when the task function raises an exception (API timeout, rate limit, JSON parse error). There is no retry logic and no explicit failure logging.

This must be fixed before the next thesis run. Without complete data, margin calculations are untrustworthy.

## Required reading

- `evals/harness/eval_runner.py` — current runner (no retry, no error handling around task fns)
- `evals/harness/arms/graph_context.py` — Arm C task fn (calls `/evaluate` API + Anthropic API, two failure points)
- `evals/harness/arms/flat_rag.py` — Arm B task fn (calls OpenAI embeddings + Anthropic API)
- `evals/harness/arms/vanilla.py` — Arm A task fn (calls Anthropic API only)
- `evals/harness/config.py` — config constants
- `docs/ISSUES.md` — "F55 eval harness missing data points" entry

## Scope

- `evals/harness/eval_runner.py` — Wrap each arm's task function with retry logic. Add `--max-retries` CLI flag (default 3). Log failures explicitly (fixture id, arm, attempt number, exception type+message) to stderr and to a structured failures file.
- `evals/harness/config.py` — Add `MAX_RETRIES` and `RETRY_DELAY_SECONDS` constants.
- `evals/harness/arms/graph_context.py` — Increase `httpx.Client` timeout from 30s to 60s (Arm C is the slowest arm; 30s is marginal for 4-guideline patients).
- `evals/results/v2-phase2-r2/` — NEW directory: re-run results after retry logic is in place. Same run parameters as F55 (`--all --run v2-phase2-r2`), same 32 fixtures, same 3 arms, 1 trial.
  - `scorecard.md` — human-readable results
  - `scorecard.json` — machine-readable results
  - `README.md` — comparison to F55 run, data completeness verification
- `docs/reference/build-status.md` — update row for F56.

## Constraints

- **Retry is per-fixture, per-arm.** If `cross-domain/case-15` Arm C fails, retry that specific call up to N times. Do not retry the entire experiment.
- **Exponential backoff.** Delay = `RETRY_DELAY_SECONDS * 2^attempt` (default: 5s, 10s, 20s). Prevents hammering rate-limited APIs.
- **Structured failure log.** Write `failures.json` to the output directory with `[{fixture, arm, attempt, error_type, error_message, timestamp}]`. This makes post-hoc debugging possible.
- **Braintrust compatibility.** The retry must happen inside the task function passed to `Eval()`, not outside it. Braintrust controls the iteration; we control what happens inside each task call.
- **No rubric changes, no arm prompt changes, no fixture changes.** This is infrastructure only + a clean re-run.

## Verification targets

- `cd evals && uv run python -m harness --all --run v2-phase2-r2` completes with 0 failures (or documents any remaining failures in `failures.json`).
- Braintrust shows 3 experiments (`v2-phase2-r2-arm-{a,b,c}`) with 32 entries each.
- `cd evals && uv run python -m harness --scorecard --run v2-phase2-r2 --output-dir results/v2-phase2-r2` produces scorecard.
- Scorecard shows N=16 for all arms on multi-guideline subset (no missing data).
- README includes data completeness table showing 96/96 entries (or explains any remaining gaps).
- README includes comparison to F55: which fixtures were previously missing and what they scored.

## Definition of done

- Retry logic implemented and tested.
- Full harness re-run completed with 0 or near-0 missing entries.
- Scorecard committed to `evals/results/v2-phase2-r2/`.
- `failures.json` committed (even if empty — proves the mechanism ran).
- README documents data completeness improvement and updated thesis margin.
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Changing arm prompts, serialization, or rubric.
- Investigating case-15's catastrophic failure (that's a serialization issue for F57).
- Changing the thesis margin or re-evaluating the gate (just report the numbers with complete data).
- Circuit breaker / kill-switch for runaway retries (3 retries per fixture is bounded enough).
