# Feature specs

Each v0 feature has a self-contained spec in this directory. The spec is the entire input needed to build the feature: context, scope, constraints, verification targets, definition of done.

## How to build one

```
/build NN
```

Or start a fresh Claude Code session and prompt: *"Build the feature in `docs/build/NN-<slug>.md`. Follow the build workflow end to end."*

Every feature runs the workflow in `docs/workflow.md`: branch, implement, test, commit, push, PR, subagent review, human merge. One feature per session. Don't batch features.

## Backlog

See [`docs/reference/build-status.md`](../reference/build-status.md) for the full backlog with status, dependencies, and PR links.

## Adding a feature

1. Copy `TEMPLATE.md` and assign the next number.
2. Fill in every section.
3. Add a row to `docs/reference/build-status.md`.

If a feature needs more than one PR, split it into numbered sub-specs rather than letting one spec sprawl.

## Rules

- Don't start a feature whose dependencies are not `shipped`.
- Don't expand scope beyond what's in the spec. If you find missing scope, amend the spec on its own branch first, then build.
- If the spec is wrong or incomplete, stop and surface it. Don't paper over it in the implementation.
