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
| 33  | Arm C convergence serialization | evals, docs           | shipped | 22                 | [33](../../docs/build/33-arm-c-convergence-serialization.md) | [#32](../../pull/32) |
| 27  | Full harness run + thesis test | evals, docs             | shipped | 22, 23, 24, 33 | [27](../../docs/build/27-full-harness-thesis-test.md) | [#34](../../pull/34), [#35](../../pull/35) |

### Phase 4: UI polish

Parallelizable with Phase 3.

| # | Feature | Components | Status | Depends on | Spec | PR |
|---|---------|------------|--------|------------|------|----|
| 28 | UI domain filter | ui, api | shipped | 20, 23, 24 | [28](../../docs/build/28-ui-domain-filter.md) | [#26](../../pull/26) |
| 29 | UI preemption/modifier viz | ui, api | shipped | 25, 26, 28 | [29](../../docs/build/29-ui-preemption-modifier-viz.md) | [#27](../../pull/27) |
| 30 | UI multi-guideline rec list | ui | shipped | 21, 29 | [30](../../docs/build/30-ui-multi-guideline-rec-list.md) | [#33](../../pull/33) |
| 31 | UI guideline-first navigation | ui, api, graph, docs | shipped | 28, 29 | [31](../../docs/build/31-ui-guideline-first-navigation.md) | [#29](../../pull/29) |
| 32 | UI cross-guideline interactions view | ui, api, docs | shipped | 25, 26, 28, 29, 31 | [32](../../docs/build/32-ui-cross-guideline-interactions-view.md) | [#30](../../pull/30) |

## v2 — deeper graph reasoning + validated interactions + scale

Macro spec: [`docs/build/v2-spec.md`](../../docs/build/v2-spec.md). Validates cross-guideline edges with clinician review, upgrades Arm B to production-quality RAG, improves Arm C serialization, and measures incremental value. Phase 2+ adds ADA Diabetes and LLM-assisted ingestion.

### Phase 1: validated interactions + stronger baseline

Each improvement is measured in isolation before the combined run. ~$2 per run, 10 min each.

| #   | Feature                                         | Components              | Status  | Depends on            | Spec                                                         | PR                   |
| --- | ----------------------------------------------- | ----------------------- | ------- | --------------------- | ------------------------------------------------------------ | -------------------- |
| 40  | Cross-guideline edge review tool                | docs, scripts           | shipped | v1 shipped            | [40](../../docs/build/40-cross-edge-review-tool.md)          | [#37](../../pull/37) |
| 41  | Re-add clinician-validated cross edges          | graph, api, evals, docs | shipped | 40 + clinician review | [41](../../docs/build/41-validated-cross-edges.md)           | [#38](../../pull/38) |
| 42  | Edge-value thesis run                           | evals, docs             | shipped | 41                    | [42](../../docs/build/42-edge-value-thesis-run.md)           | [#39](../../pull/39) |
| 43  | Arm B retrieval upgrade (section + multi-query) | evals, docs             | shipped | v1 shipped            | [43](../../docs/build/43-arm-b-retrieval-upgrade.md)         | [#41](../../pull/41) |
| 44  | Arm B upgrade thesis run                        | evals, docs             | shipped | 43                    | [44](../../docs/build/44-arm-b-upgrade-thesis-run.md)        | [#42](../../pull/42) |
| 45  | Arm C serialization v2 (concise + intensity)    | evals, docs             | shipped | v1 shipped            | [45](../../docs/build/45-arm-c-serialization-v2.md)          | [#43](../../pull/43) |
| 46  | Serialization v2 thesis run                     | evals, docs             | shipped | 45                    | [46](../../docs/build/46-serialization-thesis-run.md)        | [#44](../../pull/44) |
| 48  | Expand multi-guideline fixtures                 | evals, docs             | shipped | 42                    | [48](../../docs/build/48-expand-multi-guideline-fixtures.md) | [#40](../../pull/40) |
| 47  | v2 Phase 1 combined thesis run                  | evals, docs             | shipped | 42, 44, 46, 48        | [47](../../docs/build/47-v2-phase1-combined-run.md)          | [#45](../../pull/45) |
| 49  | Arm C completeness fixes                        | evals, graph, docs      | shipped     | 47                | [49](../../docs/build/49-arm-c-completeness-fixes.md)        | [#47](../../pull/47) |
| 50  | Arm C scoring leverage                          | evals, docs             | shipped     | 49                | [50](../../docs/build/50-arm-c-scoring-leverage.md)          | [#48](../../pull/48) |
| 51  | F50 scoring leverage thesis run                 | evals, docs             | shipped     | 50                | [51](../../docs/build/51-f50-scoring-leverage-thesis-run.md) | [#49](../../pull/49) |

### Phase 2: ADA Diabetes + multi-morbidity

Adds ADA 2024 Diabetes as a 4th guideline, connects via clinician-reviewed cross-edges, creates multi-morbidity fixtures exercising 3-4 guidelines simultaneously, and runs the thesis gate on the expanded set.

| #   | Feature                                         | Components              | Status  | Depends on            | Spec                                                         | PR  |
| --- | ----------------------------------------------- | ----------------------- | ------- | --------------------- | ------------------------------------------------------------ | --- |
| 52  | ADA 2024 Diabetes subgraph                      | graph, docs, evals      | shipped | 20, 21, 22            | [52](../../docs/build/52-ada-diabetes-subgraph.md)           | [#50](../../pull/50) |
| 53  | ADA cross-guideline edges                       | graph, docs             | shipped | 52 + clinician review | [53](../../docs/build/53-ada-cross-guideline-edges.md)       | [#51](../../pull/51) |
| 54  | Multi-morbidity fixtures                        | evals, docs             | shipped | 53                    | [54](../../docs/build/54-multi-morbidity-fixtures.md)        | [#52](../../pull/52) |
| 55  | v2 Phase 2 thesis run                           | evals, docs             | shipped | 54                    | [55](../../docs/build/55-v2-phase2-thesis-run.md)            | [#53](../../pull/53) |
| 56  | Harness retry logic + clean re-run              | evals, docs             | in-progress | 55                | [56](../../docs/build/56-harness-retry-logic.md)             | [#54](../../pull/54) |
| 57  | Serialization scoping (filter irrelevant guidelines) | evals, api, docs   | in-progress | 56                    | [57](../../docs/build/57-serialization-scoping.md)           | —   |
| 58  | Serialization compression for 3+ guidelines      | evals, docs             | pending | 57                    | [58](../../docs/build/58-serialization-compression.md)       | —   |

## Archived

| Feature | Reason |
|---------|--------|
| Ingestion pipeline | Deferred until LLM-assisted drafting returns. |
| CRC seed + fixtures | Superseded by statins (ADR 0013). |
| Review-and-flag workflow | Deferred until post-v0. |

## Update protocol

Update this file in the same PR that ships or changes the status of a feature. If a PR doesn't advance a feature, it doesn't touch this file.
