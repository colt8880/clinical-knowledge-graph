# Feature build backlog

Ordered list of features that make up v0. Each entry has its own spec file in this directory. Each spec is the entire input needed to build the feature: context, scope, constraints, verification targets, DoD.

## How to build one

```
/build NN
```

(or, equivalently, start a fresh Claude Code session and prompt: *"Build the feature in `docs/build/NN-<slug>.md`. Follow the build workflow end to end."*)

Every feature runs the workflow in `docs/workflow.md`: branch → implement → test → commit → push → PR → subagent review → human merge. One feature per session. Don't batch features — small, verifiable slices.

## Backlog

| # | Feature | Status | Depends on |
|---|---|---|---|
| 01 | Graph seed (statin model loaded into Neo4j) | shipped | — |
| 02 | API skeleton (FastAPI, `/healthz`, `/version`, `/nodes/{id}`) | shipped | 01 |
| 03 | Evaluator vertical slice (fixture 03: age-below-range exit) | pending | 02 |
| 04 | Evaluator full (remaining predicates, fixtures 01/02/04/05) | pending | 03 |
| 05 | UI Explore tab | pending | 02 |
| 06 | UI Eval tab with trace stepper | pending | 04, 05 |
| 07 | Dockerfile for `/api` | pending | 04 |
| 08 | Dockerfile for `/ui` | pending | 06 |
| 09 | `docker-compose.yml` for full stack | pending | 07, 08 |
| 10 | Contract alignment tests | pending | 02 |
| 11 | CI skeleton (GitHub Actions) | shipped | 02 |

Status values: `pending` → `in-progress` → `shipped`.

## Adding a feature

Copy `TEMPLATE.md`, assign the next number, fill in every section, add a row to the table above. If a feature needs more than one PR, split it into numbered sub-specs rather than letting one spec sprawl.

## Rules

- Don't start a feature whose dependencies are not `shipped`.
- Don't expand scope beyond what's in the spec. If you find missing scope, amend the spec on its own branch first, then build.
- If the spec is wrong or incomplete, stop and surface it. Don't paper over it in the implementation.
