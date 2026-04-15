# /ingestion

Guideline parsers, ontology mappers, and LLM-assisted drafting pipelines. Every output is drafted with full provenance and gated on clinician sign-off before merging to the production graph.

## Load before working here

1. `../docs/specs/schema.md` (provenance fields especially)
2. `../docs/specs/predicate-dsl.md` and `../docs/contracts/predicate-catalog.yaml`
3. `../docs/reference/guideline-sources.md` (running log; update after every ingestion)
4. `../docs/reference/crc-model.md` (reference shape for CRC, the v0 domain)
5. `../docs/decisions/0003-llm-assisted-ingestion.md`

## Scope

- Parsers that consume guideline PDFs/HTML and extract candidate nodes, edges, and predicate expressions
- Ontology mappers (SNOMED CT, RxNorm, LOINC, ICD-10-CM)
- LLM-assisted drafters with full provenance logging (prompt id, model version, guideline source+section, draft timestamp)
- Staging-graph writers (not production)
- Handoff to review workflow in `/review-tool`

## Not in scope here

- Production-graph writes — those happen only after clinician sign-off, via the review tool's merge action
- Patient data of any kind — ingestion is patient-agnostic
- Predicate evaluation — that's `/api`

## Build conventions

- Provenance is required on every node and edge drafted; no exceptions (ADR 0003)
- Prompts are version-controlled in this directory; prompt ids reference the committed version
- Model version is recorded as reported by the API, not inferred
- Guideline source references carry section anchors (page, heading, or URL fragment)
- Ingestion runs are reproducible: given the same prompt, model version, and source, the draft output is identical (within LLM determinism settings)
- After every production-bound ingestion, update `docs/reference/guideline-sources.md`

## Definition of done (component level)

A parser is done when:
1. It produces a draft structured representation for at least one complete guideline section
2. Every draft node and edge carries full provenance
3. Ontology mappings match the current graph node code lists (no bare ontology codes)
4. The draft validates against `predicate-catalog.yaml` shape
5. At least one end-to-end ingestion has been reviewed and signed off
