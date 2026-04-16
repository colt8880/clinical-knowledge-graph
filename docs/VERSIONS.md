# Versions

Pins the currently-implemented contract to specific versions.

## Current target (v0, statins)

| Layer | Version | Source |
|---|---|---|
| Spec tag | `spec/v2-2026-04-15` (to be tagged) | git tag |
| Graph version | `unreleased` | `docs/specs/schema.md` + `docs/reference/guidelines/statins.md` |
| Evaluator version | `unreleased` | `docs/contracts/predicate-catalog.yaml` + `docs/contracts/eval-trace.schema.json` |

Versions labeled `unreleased` mean the artifact has not been cut; consumers cite the git commit hash of the tree they built against.

## How this file works

- Every spec tag gets a row in the history table below when cut.
- Graph and evaluator versions bump independently per their own rules.
- When an implementation ships, record its target triple here.

## History

| Date | Spec tag | Graph version | Evaluator version | Notes |
|---|---|---|---|---|
| 2026-04-14 | `spec/v1-2026-04-14` (never cut) | — | — | Broad CRC-era spec; superseded before implementation. |
| 2026-04-15 | `spec/v2-2026-04-15` (pending cut) | — | — | **v0 pivot to USPSTF 2022 statins.** Trace-first evaluator (`eval-trace.md` + schema), narrowed patient-context, narrowed predicate catalog. See ADRs 0013, 0014. |

## Version bump rules (summary)

- **Spec tag:** any change to shape of a contract (predicate args, patient-context fields, schema node/edge types, trace event types) or to semantics a consumer could observe.
- **Graph version:** any change to graph schema, modeled guideline content, or value-set mapping.
- **Evaluator version:** any change to the predicate catalog, default missing-data policy, evaluation algorithm, or trace emission order.

See `specs/predicate-dsl.md` § Determinism and versioning, and ADR 0009.
