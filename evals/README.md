# Eval harness

Three-arm eval harness for the Clinical Knowledge Graph, built on [Braintrust](https://www.braintrust.dev). Measures whether graph-retrieved context (Arm C) produces better clinical next-best-action recommendations than vanilla LLM knowledge (Arm A) or flat RAG (Arm B).

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- `ANTHROPIC_API_KEY` environment variable (required for all arms + judge)
- `OPENAI_API_KEY` environment variable (required for Arm B embeddings)
- `BRAINTRUST_API_KEY` environment variable (required for experiment logging)
- Running API server at `http://localhost:8000` (required for Arm C)

## Setup

```sh
cd evals
uv sync
```

Create a `.env` file in `evals/`:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
BRAINTRUST_API_KEY=...
```

## Running

Each arm runs as a separate Braintrust experiment, enabling side-by-side comparison in the UI.

### All fixtures, all arms

```sh
cd evals
uv run python -m harness --all --run my-run-name
```

Creates 3 experiments in Braintrust: `my-run-name-arm-a`, `my-run-name-arm-b`, `my-run-name-arm-c`.

### Single arm

```sh
uv run python -m harness --all --arm c --run my-run-name
```

### Single fixture

```sh
uv run python -m harness --fixture cross-domain/case-04 --arm c --run test
```

### By guideline

```sh
uv run python -m harness --guideline statins --run statin-test
```

### Options

- `--run NAME` — experiment name prefix (default: `v1-thesis`)
- `--arm {a,b,c}` — run a single arm only
- `--trial-count N` — number of trials per input for self-consistency (default: 1)
- `--api-base URL` — override the evaluator API URL (default: `http://localhost:8000`)

## Generating scorecards

After running, generate a scorecard from Braintrust results:

```sh
uv run python -m harness --scorecard --run my-run-name
```

This fetches results from Braintrust, evaluates the thesis gate, and writes:
- `evals/results/v1-thesis/scorecard.md` — human-readable report
- `evals/results/v1-thesis/scorecard.json` — machine-readable data
- `evals/results/v1-thesis/README.md` — summary

## Rubric

See `evals/rubric.md` for the full rubric. Summary:

- 4 dimensions scored 1-5 by an LLM judge (Claude Opus 4)
- Composite = arithmetic mean
- Scores normalized to 0-1 for Braintrust display (multiply by 4, add 1 for raw scale)
- Deterministic structural checks run alongside but are not included in the composite
- Rubric version changes trigger full re-scoring

## Architecture

```
harness/
  eval_runner.py      # Entry point: Braintrust Eval() calls
  fixtures.py         # Fixture discovery and dataset loading
  judge.py            # LLM judge + structural checks + Braintrust scorer
  scorecard.py        # Aggregation, thesis gate, self-consistency
  report.py           # Markdown/JSON report generation
  serialization.py    # Arm C context building (trace + convergence)
  config.py           # Pinned models, paths, constants
  arms/
    vanilla.py        # Arm A: patient-only prompt
    flat_rag.py       # Arm B: RAG chunking + embedding + retrieval
    graph_context.py  # Arm C: graph eval + convergence summary
```
