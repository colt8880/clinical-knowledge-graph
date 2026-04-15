# 0015. Build workflow and PR review loop

Status: Accepted
Date: 2026-04-15

## Context

Stage 0 of the repo established specs, contracts, and fixtures. Stage 1 onward ships code. Claude Code will be doing most of the authoring under Colton's direction, and without a written workflow the repo will accrete in ad-hoc ways: branches pushed straight to main, PRs without manual-test evidence, reviews that rubber-stamp a diff. Claude will not self-correct these habits; they have to be written down and enforced on every PR.

The loop also has to work before CI exists. Wiring CI in the same PR that introduces the workflow conflates two concerns — the human-driven review loop needs to be exercised at least once on its own before any step in it gets automated away.

## Decision

Every feature follows the loop documented in `docs/workflow.md` and summarized in root `CLAUDE.md` under "Build workflow":

- Branch off `main` with a typed prefix (`feat/`, `fix/`, `chore/`). No direct pushes to `main`.
- Logical commits with *why* messages, not one mega-commit at the end.
- Tests must pass locally before the PR opens. PR body carries Scope, Manual Test Steps, and Manual Test Output.
- The `pr-reviewer` subagent (`.claude/agents/pr-reviewer.md`) reviews every PR and posts its review as a comment before a human looks at it.
- Claude addresses the subagent's blocking issues and actionable non-blocking suggestions on the same branch. Only then does the human review. The human merges. Claude never merges its own PR.
- CI is deferred to a later PR, after the first feature lands cleanly under this loop.

## Alternatives considered

- **No written workflow; rely on reviewer judgment.** Rejected. Colton is reviewing alongside other work; without a written loop Claude will skip steps and the review debt compounds. The workflow is what makes lightweight review possible.
- **Wire CI in this same PR.** Rejected. Conflates two changes, and the manual loop needs to be exercised once before any step in it is automated, so we know what the subagent actually catches vs. what CI should catch.
- **Skip the subagent review; human reviews everything directly.** Rejected. The subagent is a cheap filter that enforces repetitive checks (contract/spec pairing, manual-test evidence, determinism greps) so the human review can focus on substance. Instruction to "find at least three substantive things" is explicit guardrail against LGTM stamps.
- **One ADR-free `docs/workflow.md`.** Rejected. Reversals of the workflow (e.g., "we're wiring CI, dropping the manual-output requirement") need to land as new ADRs per 0009; that only works if the workflow convention itself has an ADR to supersede.

## Consequences

- Every PR from Stage 1+ has a predictable shape. Reviewers know where to look.
- The subagent spec becomes a living document — each new component (`/graph`, `/api`, `/ui`, `/evals`) extends the checks with its own DoD items.
- The first feature PR under this workflow is the canary. If the loop feels heavy or the subagent misses obvious things, fix in a follow-up ADR before building Stage 1 further.
- When CI lands, some subagent checks (test suite passed, contract/spec pairing) will move to CI; the subagent keeps the review-quality checks humans cannot cheaply automate.

## Related

- Root `CLAUDE.md` — "Build workflow" section.
- `docs/workflow.md` — full runbook.
- `.claude/agents/pr-reviewer.md` — subagent spec.
- ADR 0009 — spec versioning via git tags (reversals are append-only ADRs).
- ADR 0010 — machine contracts paired with prose specs (enforced by pr-reviewer check #2).
