# v2: Deeper graph reasoning + validated interactions + scale

**Status**: planning
**Builds on**: v1 (thesis proven: graph context > flat RAG > vanilla LLM)

## What v1 proved

v1 demonstrated that a clinical knowledge graph providing structured context to an LLM produces better recommendations than flat RAG (+0.76 composite) or vanilla LLM knowledge (+1.16 composite) across 16 patient fixtures and 3 guidelines. The advantage comes from convergence visibility — the graph's structural ability to surface that multiple guidelines independently recommend the same therapeutic actions.

v1 left several capabilities on the table. v2 picks them up.

## v2 thesis

**Cross-guideline conflict resolution and a fourth guideline (ADA Diabetes) produce measurably better recommendations than convergence alone, particularly on complex multi-morbidity patients where guidelines disagree.**

v1 measured agreement. v2 measures disagreement resolution + agreement on a harder patient population.

## Work streams

### 1. Clinician-validated cross-guideline edges

**The biggest unfinished v1 item.** 15 cross-guideline edges (PREEMPTED_BY, MODIFIES) were removed after LLM-authored modeling errors were found. The graph can express conflict resolution — the evaluator code shipped in F25/F26 — but the edges themselves need clinician sign-off.

Scope:
- Design a review workflow (UI tool or structured spreadsheet) that presents each proposed edge with source and target Rec eligibility criteria side by side.
- Clinician validates overlapping eligibility, classifies as preemption/modifier/no-interaction, signs off with rationale.
- Re-add validated edges to seeds. Run the eval harness and measure incremental value of edges on top of convergence.
- This is the cleanest possible A/B test: same fixtures, same rubric, graph-with-edges vs graph-without-edges. If edges improve Integration scores, the curated reasoning layer adds value. If not, convergence is sufficient and edges are documentation, not reasoning.

**Why this is #1:** It unblocks a clean follow-up thesis measurement and addresses the biggest open item in `docs/ISSUES.md`.

### 2. ADA Standards of Care (Diabetes)

**Why ADA:** CKD modifies diabetes medication selection — this is the canonical cross-guideline modifier example. SGLT2 inhibitors appear in both KDIGO (for renal protection) and ADA (for glycemic control). Metformin dosing depends on eGFR. Adding ADA creates a 4-guideline graph where a single patient (diabetic with CKD and cardiovascular risk) exercises every interaction type: convergence, preemption, and modification.

Scope:
- Hand-author ADA 2024 Standards of Care (pharmacologic therapy chapter) as a subgraph.
- New fixtures: diabetes-only (4), diabetes + CKD (3), diabetes + cardiovascular + CKD (2). The 2-3 multi-domain fixtures become the hardest test cases in the harness.
- Cross-guideline edges: ADA ↔ KDIGO (SGLT2, metformin), ADA ↔ ACC/AHA (statin for diabetic patients). These are clinician-reviewed from the start — no LLM-authored edges.

**Why not ACIP:** Immunization guidelines are pure lookup tables. Flat RAG handles them well. They don't exercise graph reasoning capabilities and wouldn't differentiate Arm B from Arm C.

### 3. Stronger Arm B (fair comparison)

**The eval results are only as credible as the baseline.** v1's Arm B uses naive RAG: 500-token chunks, single embedding query, top-5 by cosine similarity. A skeptic could argue the graph isn't beating RAG — it's beating bad RAG.

Scope:
- Section-level retrieval instead of arbitrary chunking. Guidelines have natural structure; use it.
- Multi-query retrieval: build separate queries for each patient condition, medication, and risk factor. Deduplicate and rerank.
- Test with a reranking step (cross-encoder or LLM reranker).
- Re-run the harness with improved Arm B. If the gap shrinks, document it honestly. If it holds, the structural advantage is validated against production-quality RAG.

### 4. Prompt and serialization tuning

**Completeness was the weakest dimension in v1 (3.50/5 for Arm C).** The LLM is missing expected actions even with full graph context. Two levers:

- **System prompt improvements:** Instruct the LLM to be exhaustive — "list every action supported by the provided guidelines." Currently the prompt says "provide recommendations" which invites the LLM to be selective.
- **Convergence serialization v2:** The current serialization lists every shared medication node (7 statins × 3 guidelines = a wall of text). A more concise summary at the recommendation level ("moderate-intensity statin therapy, supported by USPSTF Grade C, ACC/AHA COR I, KDIGO 1A") would reduce context volume and improve LLM attention.
- **Intensity/dosing context:** The graph knows medication intensity classifications but the serialization doesn't surface them. Adding "moderate-intensity: atorvastatin 10-20mg, rosuvastatin 5-10mg" vs "high-intensity: atorvastatin 40-80mg, rosuvastatin 20-40mg" would help the LLM recommend the right intensity.

### 5. LLM-assisted ingestion

**Hand-authoring guidelines doesn't scale.** v0 and v1 hand-authored 3 guidelines. Each took 1-2 days. At that rate, covering the ~20 guidelines relevant to primary care would take a month.

Scope:
- Un-archive the `/ingestion` pipeline.
- LLM reads a guideline PDF/text, proposes nodes, edges, and structured eligibility predicates.
- Clinician reviews and edits in a structured UI (not raw Cypher).
- Validated output becomes a seed file. Every node carries provenance back to the source document.
- The clinician-in-the-loop review from work stream #1 extends naturally to ingested content.

**Gate:** Don't ship LLM-assisted ingestion until the clinician review workflow from #1 is proven on the hand-authored edges. Otherwise you're automating a process that has no quality gate.

### 6. Eval infrastructure improvements

- **CI-integrated eval runs:** Run the harness on PR merge (or nightly) so regressions are caught automatically. Requires cost budgeting — 48 Opus judge calls per run at ~$2/run.
- **Cross-vendor arm validation:** Run arms with GPT-4, Gemini, and open-source models. Tests whether the graph advantage is model-specific or general. If Arm C beats Arm B across model families, the structural argument is much stronger.
- **Clinician-validated fixture scoring:** Have a clinician score a sample of arm outputs independently, then compare to LLM judge scores. Calibrates the rubric against clinical ground truth.
- **Historical replay:** Run the same fixtures against different graph versions (before/after edge additions, before/after new guidelines) to measure incremental value over time.

### 7. Live ASCVD calculation

v0-v1 fixtures supply `risk_scores.ascvd_10yr` as a pre-computed value. A real system would compute it from patient data using the Pooled Cohort Equations. Scope: implement PCE calculation in the evaluator, remove the supplied-score shortcut, validate against reference implementations. This is a prerequisite for connecting to real EHR data.

## Phasing

### Phase 1: Validated interactions + stronger baseline
- Clinician review workflow + edge re-addition (#1)
- Stronger Arm B (#3)
- Re-run thesis with edges and improved RAG
- Prompt/serialization tuning (#4)

### Phase 2: Scale the graph
- ADA Diabetes subgraph (#2)
- New multi-morbidity fixtures (diabetic + CKD + CVD)
- Thesis run on expanded fixture set

### Phase 3: Scale the pipeline
- LLM-assisted ingestion (#5)
- CI-integrated evals (#6)
- Cross-vendor validation (#6)

### Phase 4: Production readiness
- Live ASCVD calculation (#7)
- Historical replay (#6)
- Clinician-validated scoring (#6)

## Out of scope for v2

- PHI / EHR integration / multi-tenant access control. The graph stays synthetic-data-only.
- Oncology, psychiatry, obstetrics, pediatrics. v2 stays in cardiometabolic/renal primary care.
- Real-time clinical decision support deployment. This is a research tool, not a production CDS.
- Mobile or patient-facing interfaces.

## Success criteria

1. Clinician-reviewed cross-guideline edges re-added and validated.
2. ADA Diabetes subgraph live with 4+ single-guideline and 2+ multi-domain fixtures.
3. Arm B upgraded to section-level retrieval + multi-query. Arm C still beats Arm B by ≥ 0.5 on multi-guideline fixtures with the improved baseline.
4. Arm C handles a 4-guideline patient (diabetes + CKD + cholesterol + statin primary prevention) correctly — all applicable recommendations surfaced with correct convergence and conflict resolution.
5. At least one eval run with a non-Anthropic model (GPT-4 or Gemini) showing the structural advantage is not model-specific.

## Risks

- **Clinician availability.** Edge review and fixture validation require clinician time. This is the primary bottleneck, not engineering.
- **ADA scope creep.** The ADA Standards of Care is massive (200+ pages). v2 should scope to pharmacologic therapy for type 2 diabetes only, not the full standard.
- **Stronger Arm B closes the gap.** If production-quality RAG matches the graph, the thesis weakens. This is a real finding, not a failure — it would mean the graph's value is in auditability and structure, not in recommendation quality. Document honestly.
- **LLM-assisted ingestion quality.** If LLM-proposed nodes have the same modeling errors as the v1 cross-guideline edges, the ingestion pipeline becomes a source of risk rather than efficiency. The clinician review gate is non-negotiable.
