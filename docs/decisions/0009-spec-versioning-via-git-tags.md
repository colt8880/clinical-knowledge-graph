# 0009. Spec versioning via git tags, not inline version strings

Status: Accepted
Date: 2026-04-14

## Context

Specs previously carried inline version strings (`**Status: v0.**`, `**Status: v1.**`). In practice every edit to the spec bumped the version conceptually even without a tag, and nothing in the repo pinned a specific "v1" to a specific commit. Consumers (the evaluator, the adapter, the review tool) had no reliable way to say "I target spec v1" and have that mean something precise.

Separately, runtime artifacts (graph version, evaluator version) are versioned independently and that works well; we are not changing it.

## Decision

Spec versioning is expressed via git tags of the form `spec/vN-YYYY-MM-DD` (e.g., `spec/v1-2026-04-14`). The tag is the pin. Inline version strings on specs are retained for human legibility (they show the reader roughly where the spec sits), but they are advisory, not authoritative. `docs/VERSIONS.md` records the currently-implemented pin set: which spec tag, which graph version, which evaluator version.

Edits between tags are "unreleased." Any implementation that needs to target stable shape targets a tag.

## Alternatives considered

- **Inline version strings as source of truth, bumped per-edit.** Rejected: in practice we don't bump per-edit, and "v1" across different commits means different things.
- **Semver on each spec file.** Rejected: too much bookkeeping for a ~10-file spec corpus; tags cover the same need with existing tooling.
- **No spec versioning, just "read latest.".** Rejected: implementations need a stable target; unreleased edits cannot break deployed builds silently.

## Consequences

- Releases (and Claude Code build targets) cite a spec tag.
- Inline "Status: v1" lines stay but are now purely descriptive.
- API response payloads and evaluator output stamp the spec tag alongside graph version and evaluator version.
- Changelog blocks at the bottom of specs still record what changed; they're the narrative pairing the tags.

## Related

- `docs/VERSIONS.md`
- `docs/contracts/README.md`
