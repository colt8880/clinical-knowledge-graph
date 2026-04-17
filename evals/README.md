# Eval harness

Three-arm eval harness for the Clinical Knowledge Graph. Measures whether graph-retrieved context (Arm C) produces better clinical next-best-action recommendations than vanilla LLM knowledge (Arm A) or flat RAG (Arm B).

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- `ANTHROPIC_API_KEY` environment variable (required for all arms + judge)
- `OPENAI_API_KEY` environment variable (required for Arm B embeddings)
- Running API server at `http://localhost:8000` (required for Arm C)
- Optional: `BRAINTRUST_API_KEY` for Braintrust logging

## Setup

```sh
cd evals
uv sync
```

Or create a `.env` file in `evals/`:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
BRAINTRUST_API_KEY=...  # optional
```

## Running

### Single fixture, single arm

```sh
cd evals
uv run python -m harness.runner --fixture statins/01-high-risk-55m-smoker --arm a
```

### Single fixture, all arms

```sh
uv run python -m harness.runner --fixture statins/01-high-risk-55m-smoker
```

### All fixtures, all arms

```sh
uv run python -m harness.runner --all
```

### Convenience wrapper

```sh
./scripts/run-eval.sh                    # all fixtures, all arms
./scripts/run-eval.sh --arm a            # all fixtures, arm A only
./scripts/run-eval.sh --fixture statins/01-high-risk-55m-smoker --arm c
```

### Options

- `--force` — ignore cache, re-run all arms and re-score
- `--api-base URL` — override the evaluator API URL (default: `http://localhost:8000`)

## Cache

Arm outputs are cached at `evals/fixtures/<guideline>/<id>/arms/<arm>/`. A cached output is reused when the fixture, prompt template, context, and model version all match.

### Invalidating cache

- **Change a prompt template** → all fixtures for that arm invalidate
- **Change a fixture's patient.json** → that fixture's cache for all arms invalidates
- **Change guideline prose** (docs/reference/guidelines/*.md) → Arm B cache invalidates
- **Change the arm model** (in `harness/config.py`) → all caches invalidate
- **Use `--force`** → bypass cache entirely

Score cache additionally keys on rubric version and judge model.

## Reading results

### Local results

Results are written to `evals/results/<timestamp>/`:

- `results.json` — full per-fixture, per-arm scores
- `scorecard.txt` — human-readable summary table

### Braintrust

If `BRAINTRUST_API_KEY` is set, results are also logged to the `clinical-knowledge-graph` project in Braintrust. Each run creates a new experiment with per-fixture scores.

## Rubric

See `evals/rubric.md` for the full rubric. Summary:

- 4 dimensions scored 1-5 by an LLM judge (Claude Opus 4.6)
- Composite = arithmetic mean
- Deterministic structural checks run alongside but are not included in the composite
- Rubric version changes trigger full re-scoring
