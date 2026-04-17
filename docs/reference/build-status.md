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

## v1 — multi-guideline graph + three-arm eval harness

Macro spec: [`docs/build/v1-spec.md`](../../docs/build/v1-spec.md). Adds ACC/AHA 2018 Cholesterol and KDIGO 2024 CKD as subgraphs, activates cross-guideline `PREEMPTED_BY` and new `MODIFIES` edges, and stands up a three-arm eval harness (vanilla LLM / flat RAG / graph-context LLM) with Braintrust integration. Thesis gate in F27.

Required ADRs (draft alongside Phase 1; merge before the corresponding feature): 0017 preemption precedence, 0018 MODIFIES semantics, 0019 three-arm eval methodology.

### Phase 1: foundation

| # | Feature | Components | Status | Depends on | Spec | PR |
|---|---------|------------|--------|------------|------|----|
| 20 | Shared clinical entity layer | graph, api, docs | shipped | v0 shipped | [20](../../docs/build/20-shared-clinical-entity-layer.md) | [#18](../../pull/18) |
| 21 | Multi-guideline evaluator + trace extension | api, docs | shipped | 20 | [21](../../docs/build/21-multi-guideline-evaluator.md) | [#19](../../pull/19) |
| 22 | Eval harness skeleton (three arms + Braintrust) | evals, api, docs | shipped | 21 | [22](../../docs/build/22-eval-harness-skeleton.md) | [#20](../../pull/20) |

### Phase 2: independent guideline graphs

| # | Feature | Components | Status | Depends on | Spec | PR |
|---|---------|------------|--------|------------|------|----|
| 23 | ACC/AHA 2018 Cholesterol subgraph | graph, docs, evals | shipped | 20, 21, 22 | [23](../../docs/build/23-accaha-cholesterol-subgraph.md) | [#21](../../pull/21) |
| 24 | KDIGO 2024 CKD subgraph | graph, docs, evals | shipped | 20, 21, 22 | [24](../../docs/build/24-kdigo-ckd-subgraph.md) | [#22](../../pull/22) |

### Phase 3: cross-guideline connection + thesis test

| #   | Feature                        | Components              | Status  | Depends on         | Spec                                                  | PR                   |
| --- | ------------------------------ | ----------------------- | ------- | ------------------ | ----------------------------------------------------- | -------------------- |
| 25  | Preemption, USPSTF ↔ ACC/AHA   | graph, api, docs, evals | shipped | 23                 | [25](../../docs/build/25-preemption-uspstf-accaha.md) | [#24](../../pull/24) |
| 26  | MODIFIES edges from KDIGO      | graph, api, docs, evals | shipped | 24, 25             | [26](../../docs/build/26-modifies-edges-kdigo.md)     | [#25](../../pull/25) |
| 27  | Full harness run + thesis test | evals, docs             | pending | 22, 23, 24, 25, 26 | [27](../../docs/build/27-full-harness-thesis-test.md) | —                    |

### Phase 4: UI polish

Parallelizable with Phase 3.

| # | Feature | Components | Status | Depends on | Spec | PR |
|---|---------|------------|--------|------------|------|----|
| 28 | UI domain filter | ui, api | shipped | 20, 23, 24 | [28](../../docs/build/28-ui-domain-filter.md) | [#26](../../pull/26) |
| 29 | UI preemption/modifier viz | ui, api | in-progress | 25, 26, 28 | [29](../../docs/build/29-ui-preemption-modifier-viz.md) | — |
| 30 | UI multi-guideline rec list | ui | pending | 21, 25, 26, 29 | [30](../../docs/build/30-ui-multi-guideline-rec-list.md) | — |

## v0.1 — stretch goals (deferred)

No features assigned. Candidates: live ASCVD/PCE calculation, boundary-age fixtures, missing-lipid-panel semantics. Likely rolls into v1 fixtures organically as cross-domain cases surface them; revisit after v1 ships.

## post-v1

No features assigned yet. Candidates: ADA Standards of Care, ACIP immunizations, multi-morbidity archetype patient (5-domain), LLM-assisted ingestion, historical replay, cross-vendor arm validation, CI-integrated eval runs.

## Archived

| Feature | Reason |
|---------|--------|
| Ingestion pipeline | Deferred until LLM-assisted drafting returns. |
| CRC seed + fixtures | Superseded by statins (ADR 0013). |
| Review-and-flag workflow | Deferred until post-v0. |

## Update protocol

Update this file in the same PR that ships or changes the status of a feature. If a PR doesn't advance a feature, it doesn't touch this file.
