# Clinical Knowledge Graph

## Purpose

Build a clinical knowledge graph that serves as a deterministic reasoning substrate for an agentic EHR/LLM system. The graph encodes published clinical guidelines as structured nodes and edges; an evaluator traverses it against a `PatientContext` and emits an auditable `EvalTrace`.

## v0 scope

**One guideline, end to end:** USPSTF 2022 statin primary prevention (Grade B / C / I).

Four deliverables:

1. **Graph** — statin model loaded into Neo4j with full provenance.
2. **Evaluator + API** (`/api`, Python) — trace-first evaluator behind a REST API. Trace is primary output; the recommendation list is a derived view over the trace.
3. **UI** (`/ui`, Next.js) — one app, two tabs:
   - **Explore**: manual graph traversal, like the existing `diagrams/crc-graph.html` but live against the API.
   - **Eval**: pick a fixture, run it, step through the trace event by event, highlight the current node on the graph.
4. **Evals** (`/evals/fixtures/statins/`) — 5 synthetic patient fixtures covering Grade B, Grade C, age-below-range exit, Grade I, and secondary-prevention exit.

See ADR 0013 (guideline selection) and ADR 0014 (v0 scope and structure).

## Core design principles

- **Determinism over cleverness.** Same `PatientContext` + same graph version + same evaluator version produces a byte-identical trace.
- **Trace-first.** The evaluator emits an event stream (`EvalTrace`). Recommendations are derived from the trace, not the other way around. This makes the Eval UI a natural demo and the audit log free.
- **Provenance is non-negotiable.** Every node and edge traces back to a specific guideline, version, section, and publication date.
- **Clinician-reviewable by construction.** Human-legible labels on every edge; reviewers should not need to read code to understand a path.
- **Schema tolerates versioning.** Historical replay is deferred in v0 but the schema supports it.
- **Separation of knowledge from patient data.** Zero PHI in this repo. Synthetic fixtures only.

## Resolved design decisions

Each decision has a full ADR in `docs/decisions/`. Summary:

1. Neo4j Community for v0 (0001).
2. FHIR-aligned clinical entity layer with SNOMED / RxNorm / LOINC / ICD-10-CM / CPT code lists (0002).
3. ~~CRC only for v0~~ — **superseded by 0013.** v0 is statins.
4. Internal REST API between consumers and graph (0005).
5. Next.js + Cytoscape.js for the UI (0004).
6. LLM-assisted ingestion with mandatory clinician sign-off (0003). Deferred in v0; statin model is hand-authored.
7. Homegrown predicate DSL (0007).
8. Pregnancy as a top-level structured record (0008). Accepted but deferred in v0.
9. Spec versioning via git tags (0009).
10. Machine contracts paired with prose specs (0010).
11. Statins as v0 guideline (0013; supersedes 0006).
12. v0 scope, `/ui` rename, Python for `/api`, trace-first evaluator (0014).
13. Build workflow and PR review loop (0015).
14. Guideline content layout (0016).

## Schema summary

Split into a **knowledge layer** (`Guideline`, `Recommendation`, `Strategy`) and a **FHIR-aligned clinical entity layer** (`Condition`, `Observation`, `Medication`, `Procedure`).

`Recommendation` carries `evidence_grade`, `intent`, `trigger`, `structured_eligibility` (JSON predicate tree), `clinical_nuance`, and `provenance`. A Rec `OFFERS` one or more `Strategy` nodes; each Strategy's `INCLUDES_ACTION` edges point at clinical entity nodes with `cadence`/`lookback`/`priority`/`intent`. Strategy semantics are conjunction: all included actions must be satisfied for the Strategy to count as satisfied. A Rec is up-to-date when any offered Strategy is satisfied.

For the statin model specifically: one Rec per USPSTF grade band, one moderate-intensity Strategy that fans out to seven statin medications at the class level (any one active prescription satisfies), and one shared-decision-making Strategy for the Grade C path.

Cross-guideline `PREEMPTED_BY` edges are in the schema but not exercised in v0 (single guideline).

**Before modifying node types, edge types, or schema conventions, read `docs/specs/schema.md`.**

## Repo layout

```
/graph
  /seeds           # per-guideline Cypher seeds (e.g. statins.cypher)
  constraints.cypher
/api               # Python/FastAPI evaluator + REST API (has CLAUDE.md)
/ui                # Next.js app: Explore tab + Eval tab (has CLAUDE.md)
/evals
  /fixtures        # per-guideline fixture dirs (e.g. fixtures/statins/)
  SPEC.md
  INVENTORY.md
/diagrams          # visual artifacts (HTML/SVG/Mermaid)
/scripts           # helper scripts (seed, codegen, etc.)
/docs
  /specs           # rationale + semantics
  /contracts       # machine-readable shape (JSON Schema, OpenAPI, predicate catalog)
  /reference
    /guidelines    # per-guideline modeling docs (e.g. guidelines/statins.md)
  /decisions       # ADRs, append-only
  /archive         # retired specs (review-workflow, crc-model, etc.)
  VERSIONS.md
  ISSUES.md
```

Guideline content layout is a v0 bootstrap; see ADR 0016 for the scaling plan.

Ingestion (`/ingestion`) is archived for v0 — statin model is hand-authored. Will un-archive when LLM-assisted ingestion lands.

Each code directory has its own `CLAUDE.md` with load order, scope, and DoD.

## Context files

**Specs (rationale + semantics):**

- `docs/specs/schema.md` — authoritative node/edge spec.
- `docs/specs/predicate-dsl.md` — predicate language.
- `docs/specs/patient-context.md` — evaluator input shape.
- `docs/specs/eval-trace.md` — evaluator output shape (event stream).
- `docs/specs/api-primitives.md` — traversal primitives.
- `docs/specs/ui.md` — `/ui` product spec (Explore + Eval tabs).

**Contracts (source of truth for shape):**

- `docs/contracts/predicate-catalog.yaml`
- `docs/contracts/patient-context.schema.json`
- `docs/contracts/eval-trace.schema.json`
- `docs/contracts/api.openapi.yaml`
- `docs/contracts/README.md`

**Reference:**

- `docs/reference/schema-reference.md`
- `docs/reference/guidelines/statins.md` — concrete USPSTF 2022 statin model. Replaces CRC.
- `docs/reference/guideline-sources.md`
- `docs/reference/build-status.md`

**Decisions:** `docs/decisions/README.md` + numbered ADRs, append-only.

**Cross-cutting:** `docs/VERSIONS.md`, `docs/ISSUES.md`.

**Evals:** `evals/SPEC.md`, `evals/INVENTORY.md`, `evals/fixtures/statins/README.md`.

## Working conventions for Claude

- Load the directory-specific `CLAUDE.md` when working in `/graph`, `/api`, `/ui`, or `/evals`.
- Check `docs/decisions/` before relitigating a design choice. Reversals ship as new ADRs that supersede old ones, never as edits to the old.
- Any change to field shape or predicate signature edits both `docs/specs/` and `docs/contracts/` in one commit.
- Update the backlog row in `docs/reference/build-status.md` when a feature ships or changes status.
- Log deferred work in `docs/ISSUES.md`.
- Push back on schema creep. New node types / edge types / predicates / patient-context fields need a concrete guideline requirement.
- No PHI. Synthetic data only.
- Cite the guideline in code comments and commit messages.
- Prefer Cypher over app-layer joins.
- Colton is a senior healthcare PM with an engineering background. Skip 101-level explanations; surface tradeoffs.

## Build workflow

- Features are specified in `docs/build/`. To build one, use `/build NN` (or read `docs/build/NN-*.md` and follow this workflow end to end). One feature per session.
- Every feature goes on its own branch off `main`. Branch names: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`.
- Never push directly to `main`. Never merge your own PR. The human merges.
- Commit in logical chunks. Each commit message explains the *why*, not just the *what*.
- Every feature has tests: unit where it makes sense, at least one fixture- or integration-level test that exercises the user-visible behavior.
- Run the test suite locally before opening a PR. It must pass — do not open a PR on a red suite. Paste the output into the PR body.
- Every PR body includes: **Scope** (what this does), **Manual Test Steps** (numbered, reproducible), **Manual Test Output** (the actual output of running those steps).
- Update the backlog row in `docs/reference/build-status.md` when a feature ships or changes status.
- After opening the PR, invoke the `pr-reviewer` subagent and post its output as a PR comment. If the subagent flags blocking issues or actionable suggestions, address them (push fixes to the same branch, re-run the reviewer) before handing the PR to the human. The human only reviews after the subagent's feedback has been resolved.
- If the human requests changes, push fixes to the same branch. Do not open a new PR.
- After merge: `git checkout main && git pull && git branch -d <branch>`.
- CI is deliberately not wired yet. Add it in a separate PR after the first feature merges cleanly under this workflow.

See `docs/workflow.md` for the full runbook.

## Out of scope for v0

- Any guideline other than USPSTF 2022 statin primary prevention.
- Preemption across guidelines, cascade-triggered follow-up Recs, `expects` result-conditional semantics (schema supports them; evaluator doesn't exercise them).
- Historical replay across graph versions.
- LLM-assisted ingestion; the review-and-flag workflow.
- Live ASCVD calculation via Pooled Cohort Equations. v0 fixtures supply `risk_scores.ascvd_10yr` directly.
- Secondary prevention (established ASCVD). Detected and exited, not modeled.
- PHI / EHR integration / multi-tenant access control.

## Glossary

- **Agentic EHR** — LLM-driven system that recommends or takes actions inside an EHR context.
- **Deterministic reasoning layer** — the graph + evaluator; same input + version = same output.
- **Guideline** — published, versioned clinical recommendation document (USPSTF, ACC/AHA, specialty society).
- **Recommendation** — single actionable statement, tied to criteria and an action.
- **Strategy** — a conjunction of one or more actions that together satisfy a Rec.
- **EvalTrace** — ordered stream of evaluator events. Primary output; recommendations are a derived view.
- **Preemption** — cross-guideline conflict resolution. Schema-only in v0.
