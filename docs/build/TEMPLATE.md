# NN: <title>

**Status**: pending | in-progress | shipped
**Depends on**: NN, NN (or —)
**Components touched**: graph / api / ui / evals / ci / docs
**Branch**: `feat/<slug>` | `chore/<slug>` | `fix/<slug>`

## Context

Why this feature exists. What it unblocks. Link out to the specs and ADRs that ground it. Keep to 3-5 sentences; the reader already has `CLAUDE.md` loaded.

## Required reading

Files the implementer MUST read before writing code. Be specific (path + why).

- `path/to/spec.md` — <why this matters for this feature>

## Scope

Exact list of files to create or modify. If a file isn't listed here, this feature doesn't touch it.

- `path/new-file.ext` — <purpose>
- `path/existing-file.ext` — <what changes>

## Constraints

Non-negotiables: language/runtime versions, libraries to prefer or avoid, performance targets, invariants that must hold. Include deterministic-output constraints where relevant.

## Verification targets

What the implementer must prove works before opening the PR. Each target should be objectively checkable — a command that exits 0, a count that matches, a fixture whose golden output matches.

- <target 1 — how to verify>
- <target 2 — how to verify>

## Definition of done

- All scope files exist and match constraints.
- All verification targets pass locally.
- Tests written (unit where sensible, at least one integration-level test exercising user-visible behavior).
- `docs/reference/build-status.md` backlog row updated.
- PR opened with Scope / Manual Test Steps / Manual Test Output in the body.
- `pr-reviewer` subagent run; blocking feedback addressed; output posted as PR comment.

## Out of scope

Explicit list of things the implementer might be tempted to do but must not. Defer these to a later feature or a follow-up issue.

- <thing 1>
- <thing 2>
