# 42: Arm B retrieval upgrade (section-level + multi-query)

**Status**: pending
**Depends on**: v1 shipped
**Components touched**: evals / docs
**Branch**: `feat/arm-b-retrieval-upgrade`

## Context

v1's Arm B uses naive RAG: 500-token chunks with a single embedding query, top-5 by cosine similarity. The v1 thesis result (graph context beats flat RAG by +0.76 composite) is only credible if the RAG baseline is reasonably strong. A skeptic could argue we're beating bad RAG, not proving graph value.

This feature upgrades Arm B to production-quality retrieval so the comparison is fair.

## Required reading

- `evals/harness/arms/flat_rag.py` — current Arm B implementation
- `docs/reference/guidelines/statins.md`, `cholesterol.md`, `kdigo-ckd.md` — the source docs Arm B chunks from
- `evals/harness/config.py` — chunking parameters

## Scope

- `evals/harness/arms/flat_rag.py` — MODIFY. Three improvements:
  1. **Section-level chunking.** Replace 500-token arbitrary chunks with section-aware splitting. Guidelines have `##` headers; split on those boundaries. Each chunk is a complete section with its header preserved for context. Fall back to token-based splitting only for sections that exceed 1000 tokens.
  2. **Multi-query retrieval.** Build separate embedding queries for each distinct clinical concern in the patient context: one per active condition, one per medication class, one for risk scores. Retrieve top-3 per query, deduplicate by chunk ID, return up to 8 unique chunks (vs current top-5).
  3. **Query construction improvement.** Current query is a flat list of demographics + conditions. New query includes clinical framing: "55-year-old male with hypertension, CKD stage 3a (eGFR 52), ASCVD risk 8.5%. What are the guideline recommendations for statin therapy, CKD management, and cardiovascular risk reduction?"

- `evals/harness/config.py` — MODIFY. Update chunking parameters: `CHUNK_STRATEGY = "section"`, `TOP_K_PER_QUERY = 3`, `MAX_UNIQUE_CHUNKS = 8`.

- `evals/tests/test_flat_rag.py` — NEW. Unit tests for section-aware chunking:
  - Given a markdown doc with `##` headers, chunks split on headers.
  - Each chunk includes its header.
  - Multi-query deduplication works correctly.

- `evals/SPEC.md` — MODIFY. Update Arm B chunking section.

## Constraints

- Embedding model stays `text-embedding-3-small`. Don't change the embedding model in this feature — that's a separate variable.
- The upgrade must not add reranking yet. Reranking is a potential F43 if the section-level upgrade doesn't close the gap enough. Keep variables isolated.
- Cross-guideline map files remain excluded (per the v1 fix).
- Cache invalidation: changing Arm B's retrieval changes the context hash, so all Arm B cached outputs automatically invalidate. This is correct.

## Verification targets

- `cd evals && uv run pytest tests/test_flat_rag.py -v` — all new tests pass.
- Manual: run Arm B on `cross-domain/case-04` (3-guideline patient). Inspect retrieved chunks. Verify chunks come from relevant sections across all 3 guidelines (not just the top-scoring guideline).
- Manual: compare old vs new chunk quality on 2-3 fixtures. New chunks should have complete section context, not mid-paragraph fragments.

## Definition of done

- All scope files modified/created.
- Tests pass.
- Arm B retrieval demonstrably improved (chunks are section-level, multi-query covers multiple guidelines).
- `docs/reference/build-status.md` updated.
- PR opened, reviewed, merged.

## Out of scope

- Reranking (cross-encoder or LLM reranker). Separate feature if needed after measuring this upgrade's impact.
- Changing the embedding model.
- Running the full eval harness to measure impact. That's F44.
- Changing Arm B's prompt template (only retrieval changes).
