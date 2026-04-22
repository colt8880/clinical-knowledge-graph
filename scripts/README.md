# Scripts

Helper scripts for the Clinical Knowledge Graph.

## fixture_report.py

Generates a static HTML report for inspecting eval fixture results from Braintrust. Shows patient context, expected actions, arm-by-arm LLM outputs, scores with judge rationale, and graph context detail.

**Run from the `evals/` directory** (where `uv` and `.env` are configured):

```bash
cd evals

# All fixtures, all arms
uv run python ../scripts/fixture_report.py --run v2-phase1 --all

# Single fixture
uv run python ../scripts/fixture_report.py --run v2-phase1 --fixture cross-domain/case-08

# Only specific arms
uv run python ../scripts/fixture_report.py --run v2-phase1 --all --arms b,c

# Custom output path
uv run python ../scripts/fixture_report.py --run v2-phase1 --all --output /tmp/my-report.html
```

### Run names

The `--run` flag maps to Braintrust experiments named `{run}-arm-{a,b,c}`:

| Run name | Description |
|----------|-------------|
| `v1-thesis` | v1 baseline (16 fixtures) |
| `v2-edges-final` | F42: cross-guideline edges isolation |
| `v2-arm-b` | F44: upgraded Arm B retrieval isolation |
| `v2-serial` | F46: serialization v2 isolation |
| `v2-phase1` | F47: all Phase 1 improvements combined |

### Options

| Flag | Description |
|------|-------------|
| `--run NAME` | Braintrust run name (required, can specify multiple times) |
| `--all` | Generate report for all fixtures |
| `--fixture ID` | Single fixture (e.g. `cross-domain/case-08`) |
| `--arms a,b,c` | Comma-separated arm IDs to include (default: `a,b,c`) |
| `--output PATH` | Output HTML path (default: `fixture-report.html`) |

### Requirements

- `BRAINTRUST_API_KEY` in `evals/.env`
- `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` are not needed (read-only)
