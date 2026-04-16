# Backlog

Feature backlog for the Clinical Knowledge Graph. Source of truth for what's shipped, what's next, and what's blocked.

Status values: `pending` | `in-progress` | `shipped` | `blocked`.

## v0 — USPSTF 2022 statin primary prevention

| # | Feature | Components | Status | Depends on | Spec | PR |
|---|---------|------------|--------|------------|------|----|
| 01 | Graph seed (statin model into Neo4j) | graph | shipped | — | — | [#4](../../pull/4) |
| 02 | API skeleton (FastAPI, endpoints) | api | shipped | 01 | [02](../../docs/build/02-api-skeleton.md) | [#6](../../pull/6) |
| 03 | Evaluator vertical slice (fixture 03) | api, evals | shipped | 02 | [03](../../docs/build/03-evaluator-case-03.md) | [#9](../../pull/9) |
| 10 | Contract alignment tests | api, docs | shipped | 02 | [10](../../docs/build/10-contract-alignment-tests.md) | [#8](../../pull/8) |
| 11 | CI skeleton (GitHub Actions) | ci | shipped | 02 | [11](../../docs/build/11-ci-skeleton.md) | [#7](../../pull/7) |
| 04 | Evaluator full (remaining predicates) | api, evals | shipped | 03 | [04](../../docs/build/04-evaluator-full.md) | [#11](../../pull/11) |
| 05 | UI Explore tab | ui | shipped | 02 | [05](../../docs/build/05-ui-explore.md) | [#12](../../pull/12) |
| 06 | UI Eval tab with trace stepper | ui | shipped | 04, 05 | [06](../../docs/build/06-ui-eval.md) | [#13](../../pull/13) |
| 07 | Dockerfile for `/api` | api | shipped | 04 | [07](../../docs/build/07-containerize-api.md) | [#14](../../pull/14) |
| 08 | Dockerfile for `/ui` | ui | shipped | 06 | [08](../../docs/build/08-containerize-ui.md) | [#15](../../pull/15) |
| 09 | `docker-compose.yml` | ci | shipped | 07, 08 | [09](../../docs/build/09-compose.md) | [#16](../../pull/16) |

## v0.1 — stretch goals

No features assigned yet. Candidates: live ASCVD/PCE calculation, boundary-age fixtures, missing-lipid-panel semantics.

## post-v0

No features assigned yet. Candidates: second guideline, cross-guideline preemption, LLM-assisted ingestion, historical replay.

## Archived

| Feature | Reason |
|---------|--------|
| Ingestion pipeline | Deferred until LLM-assisted drafting returns. |
| CRC seed + fixtures | Superseded by statins (ADR 0013). |
| Review-and-flag workflow | Deferred until post-v0. |

## Update protocol

Update this file in the same PR that ships or changes the status of a feature. If a PR doesn't advance a feature, it doesn't touch this file.
