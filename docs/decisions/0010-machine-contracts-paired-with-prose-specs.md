# 0010. Machine contracts paired with prose specs

Status: Accepted
Date: 2026-04-14

## Context

Prose specs in `docs/specs/` mix contract (field shapes, predicate signatures) with rationale (why the shape is what it is). That is the right shape for human review. It is the wrong shape for programmatic consumers: build tools, validators, generators, and Claude Code sessions end up re-reading rationale to extract shapes, and shapes drift silently when the prose reads plausibly but the implementation diverges.

## Decision

Every prose spec that defines structural contracts is paired with a machine-readable artifact in `docs/contracts/`:

- `predicate-catalog.yaml` pairs `specs/predicate-dsl.md`.
- `patient-context.schema.json` pairs `specs/patient-context.md`.

Prose is source of truth for rationale and semantics. Machine artifact is source of truth for shape. Edits to shape happen in both, in one commit, prose-first.

## Alternatives considered

- **Prose only.** Rejected above.
- **Machine only, generate prose.** Rejected: rationale and design tradeoffs do not survive round-tripping through a machine format without degrading to comments; prose is expressive for a reason.
- **Single annotated source that projects both.** Plausible future direction but not worth the tooling investment at this stage.

## Consequences

- Reviewers of a shape change check both files are updated.
- CI (when it exists) validates the contracts and, ideally, cross-checks that the prose spec and machine contract enumerate the same items (e.g., every predicate in the catalog appears in the prose spec under a `### predicate_name` or `** predicate_name **` heading).
- Evaluator code generation, if we ever want it, reads the machine contract; rationale docs stay human-authored.

## Related

- `docs/contracts/README.md`
- `docs/contracts/predicate-catalog.yaml`
- `docs/contracts/patient-context.schema.json`
