# Eval Rubric v1

**Rubric version**: `v1`
**Last updated**: 2026-04-17

Rubric changes trigger re-scoring. Do not compare scores across rubric versions.

## Models (pinned)

| Role | Model | Version string |
|------|-------|----------------|
| Arms (A, B, C) | Claude Sonnet 4.6 | `claude-sonnet-4-6-20250514` |
| Judge | Claude Opus 4.6 | `claude-opus-4-6-20250610` |

Changing a model forces a re-score under a new rubric version.

## Temperature

All arms: temperature 0. Judge: temperature 0. Determinism is best-effort (LLMs are not bit-deterministic), but same prompt + same model + temp 0 is close enough for run-to-run comparison.

## Dimensions (1-5 each)

### 1. Completeness

Are all expected actions present in the output?

| Score | Criteria |
|-------|----------|
| 5 | All expected actions present, no missing items |
| 4 | One minor action missing that does not affect clinical outcome |
| 3 | One clinically relevant action missing |
| 2 | Multiple expected actions missing |
| 1 | Most expected actions missing or output is empty/incoherent |

### 2. Clinical Appropriateness

Are any recommendations contraindicated or clinically wrong?

| Score | Criteria |
|-------|----------|
| 5 | All recommendations are clinically appropriate; no contraindicated actions |
| 4 | All recommendations are appropriate; minor imprecision in language |
| 3 | One recommendation is questionable but not harmful |
| 2 | One contraindicated or clearly wrong recommendation present |
| 1 | Multiple contraindicated or dangerous recommendations |

### 3. Prioritization

Is sequencing reasonable (most impactful first)?

| Score | Criteria |
|-------|----------|
| 5 | Actions ordered by clinical impact; most urgent/impactful first |
| 4 | Ordering is reasonable; one minor sequencing issue |
| 3 | Ordering is partially correct; key action not prioritized appropriately |
| 2 | Ordering is largely incorrect; low-priority items before high-priority |
| 1 | No coherent ordering; random or reversed priority |

### 4. Integration

Does the output correctly handle cross-guideline interactions?

| Score | Criteria |
|-------|----------|
| 5 | Cross-guideline interactions correctly identified and resolved |
| 4 | Interactions mostly correct; one minor gap |
| 3 | Some interactions missed but no harmful conflicts |
| 2 | Significant cross-guideline conflicts unresolved |
| 1 | Cross-guideline interactions ignored entirely |

**Note**: In v1 Phase 1 (single-guideline baseline with statins only), this dimension scores **5 by default** for all arms since there is nothing to integrate. It activates starting F25/F26 when cross-guideline edges exist.

## Composite score

Composite = arithmetic mean of all 4 dimensions. No weighting in v1.

```
composite = (completeness + clinical_appropriateness + prioritization + integration) / 4
```

## Deterministic structural checks

Run separately from the LLM judge. Results logged alongside rubric scores but **not combined** into the composite for v1.

Checks per fixture:
- **expected_actions_present**: Does the output include all actions from `expected-actions.json`?
- **contraindications_absent**: Does the output avoid all actions listed in `contraindications`?
- **output_parseable**: Is the output valid JSON matching the expected schema?

## Judge prompt structure

The judge receives:
1. The patient context (demographics, conditions, medications, labs)
2. The expected actions list with rationale
3. The arm's output
4. The rubric dimensions with scoring criteria

The judge returns a JSON object with per-dimension scores and brief rationale for each score.

## Cache invalidation

Scores are cached alongside arm outputs. A score is invalidated when:
- The rubric version changes
- The judge model changes
- The arm output changes (which itself invalidates when fixture, arm prompt, context, or arm model changes)
