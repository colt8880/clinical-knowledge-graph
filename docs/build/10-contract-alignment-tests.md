# 10: Contract alignment tests

**Status**: in-progress
**Depends on**: 02
**Branch**: `feat/contract-alignment-tests`

## Context

PR #6 (API skeleton) shipped with contract drift: the OpenAPI server URL didn't match the implementation, and build-status rows weren't flipped to `shipped` in the same diff. The `pr-reviewer` subagent now has hard-blocker rules for contract alignment (added in PR #6 follow-up), but those are review-time checks — they catch drift, they don't prevent it.

This feature adds automated tests that run in the test suite and fail if implementation and contracts diverge. The reviewer rules stay as the backstop; the tests are the fast feedback loop.

## Required reading

- `.claude/agents/pr-reviewer.md` § Contract alignment — the rules these tests codify.
- `docs/contracts/api.openapi.yaml` — OpenAPI contract.
- `docs/contracts/eval-trace.schema.json` — trace event schema.
- `docs/contracts/patient-context.schema.json` — input schema.
- `docs/contracts/predicate-catalog.yaml` — predicate catalog.

## Scope

- `api/tests/test_contract_alignment.py` — pytest tests that:
  - Compare the FastAPI-generated OpenAPI schema against the committed `api.openapi.yaml` for the implemented endpoints (paths, methods, response shapes).
  - Validate that every predicate referenced in `seed.cypher` structured_eligibility trees has an entry in `predicate-catalog.yaml`.
  - Validate that `docs/build/README.md` and `docs/reference/build-status.md` are consistent (no feature marked `shipped` in one but not reflected in the other).

## Constraints

- Tests only — no enforcement hooks or CI changes in this feature.
- Tests must pass against the current repo state (they codify existing alignment, not aspirational alignment).

## Verification targets

- `cd api && python -m pytest tests/test_contract_alignment.py -v` exits 0.

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- PR opened with Scope / Manual Test Steps / Manual Test Output.
- `pr-reviewer` subagent run; blocking feedback addressed.

## Out of scope

- CI wiring (that's a separate chore).
- Pre-commit hooks.
- Eval-trace or patient-context schema validation tests (those land with features 03/04).
