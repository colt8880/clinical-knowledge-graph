"""Tests for Arm B section-level chunking and multi-query retrieval.

Covers:
- Section-aware splitting on ## headers
- Header preservation in each chunk
- Fallback token-based splitting for oversized sections
- Multi-query deduplication
- Clinical query construction
"""

from __future__ import annotations

from unittest.mock import patch

from harness.arms.flat_rag import (
    _approximate_token_count,
    _build_clinical_query,
    _build_per_concern_queries,
    _chunk_by_sections,
    _chunk_text_by_tokens,
    _compute_age,
    _cosine_similarity,
)


# --- Section-aware chunking ---


SAMPLE_MD = """\
## Guideline node

This is the guideline overview section with basic metadata.

## Recommendations

### R1 — Grade B

Initiate statin for patients aged 40-75 with ASCVD risk >= 10%.

### R2 — Grade C

Consider shared decision making for patients with ASCVD risk 7.5-10%.

## Strategies

Moderate-intensity statin therapy is the primary strategy.
"""


def test_chunk_by_sections_splits_on_headers():
    chunks = _chunk_by_sections(SAMPLE_MD)
    # Should produce 3 chunks (one per ## section)
    assert len(chunks) == 3


def test_chunk_by_sections_preserves_headers():
    chunks = _chunk_by_sections(SAMPLE_MD)
    assert chunks[0].startswith("## Guideline node")
    assert chunks[1].startswith("## Recommendations")
    assert chunks[2].startswith("## Strategies")


def test_chunk_by_sections_includes_body():
    chunks = _chunk_by_sections(SAMPLE_MD)
    assert "ASCVD risk >= 10%" in chunks[1]
    assert "shared decision making" in chunks[1]


def test_chunk_by_sections_preamble_before_first_header():
    """Text before the first ## header becomes its own chunk."""
    md = "# Title\n\nPreamble text here.\n\n## Section 1\n\nBody."
    chunks = _chunk_by_sections(md)
    assert len(chunks) == 2
    assert "Preamble" in chunks[0]
    assert chunks[1].startswith("## Section 1")


def test_chunk_by_sections_empty_input():
    assert _chunk_by_sections("") == []


def test_chunk_by_sections_no_headers():
    """Text with no ## headers stays as one chunk."""
    md = "Just plain text with paragraphs.\n\nAnother paragraph."
    chunks = _chunk_by_sections(md)
    assert len(chunks) == 1
    assert "plain text" in chunks[0]


# --- Oversized section fallback ---


def test_oversized_section_gets_split():
    """Sections exceeding MAX_SECTION_TOKENS fall back to token splitting."""
    # Build a section larger than 1000 tokens (~4000 chars)
    big_body = "\n\n".join(f"Paragraph {i} with enough text to add tokens." for i in range(120))
    md = f"## Big Section\n\n{big_body}"

    with patch("harness.arms.flat_rag.MAX_SECTION_TOKENS", 200):
        chunks = _chunk_by_sections(md)

    # Should be split into multiple sub-chunks
    assert len(chunks) > 1
    # Each sub-chunk should start with the header
    for chunk in chunks:
        assert chunk.startswith("## Big Section")


# --- Multi-query deduplication ---


def test_build_per_concern_queries_conditions():
    """Each active condition gets its own query."""
    ctx = {
        "patient": {"date_of_birth": "1970-01-01", "administrative_sex": "male"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [
            {"codes": [{"display": "Essential hypertension"}]},
            {"codes": [{"display": "Type 2 diabetes"}]},
        ],
        "medications": [],
        "risk_scores": {},
    }
    queries = _build_per_concern_queries(ctx)
    # 2 condition queries + 1 catch-all
    assert len(queries) == 3
    assert any("Essential hypertension" in q for q in queries)
    assert any("Type 2 diabetes" in q for q in queries)


def test_build_per_concern_queries_medications():
    ctx = {
        "patient": {"date_of_birth": "1970-01-01", "administrative_sex": "female"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [],
        "medications": [
            {"codes": [{"display": "Atorvastatin 40mg"}]},
        ],
        "risk_scores": {},
    }
    queries = _build_per_concern_queries(ctx)
    # 1 medication query + 1 catch-all
    assert len(queries) == 2
    assert any("Atorvastatin" in q for q in queries)


def test_build_per_concern_queries_risk_scores():
    ctx = {
        "patient": {"date_of_birth": "1970-01-01", "administrative_sex": "male"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [],
        "medications": [],
        "risk_scores": {
            "ascvd_10yr": {"value": 12.5},
        },
    }
    queries = _build_per_concern_queries(ctx)
    # 1 risk score query + 1 catch-all
    assert len(queries) == 2
    assert any("ascvd_10yr" in q for q in queries)


def test_build_per_concern_queries_multi_guideline_patient():
    """A 3-guideline patient should generate queries covering all concerns."""
    ctx = {
        "patient": {"date_of_birth": "1971-02-20", "administrative_sex": "male"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [
            {"codes": [{"display": "Essential hypertension"}]},
        ],
        "observations": [
            {
                "codes": [{"display": "eGFR"}],
                "value": {"value_quantity": {"value": 52, "unit": "mL/min/1.73m2"}},
            },
        ],
        "medications": [],
        "risk_scores": {
            "ascvd_10yr": {"value": 8.5},
        },
    }
    queries = _build_per_concern_queries(ctx)
    # 1 condition + 1 risk score + 1 catch-all = 3
    assert len(queries) == 3
    # The catch-all should frame a clinical question
    assert any("guideline recommendations" in q.lower() for q in queries)


# --- Clinical query construction ---


def test_build_clinical_query_includes_demographics():
    ctx = {
        "patient": {"date_of_birth": "1970-06-15", "administrative_sex": "female"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [],
        "medications": [],
        "risk_scores": {},
    }
    query = _build_clinical_query(ctx)
    assert "55-year-old" in query
    assert "female" in query


def test_build_clinical_query_includes_conditions():
    ctx = {
        "patient": {"date_of_birth": "1970-01-01", "administrative_sex": "male"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [
            {"codes": [{"display": "CKD stage 3a"}]},
        ],
        "medications": [],
        "risk_scores": {},
    }
    query = _build_clinical_query(ctx)
    assert "CKD stage 3a" in query


def test_build_clinical_query_includes_risk_scores():
    ctx = {
        "patient": {"date_of_birth": "1970-01-01", "administrative_sex": "male"},
        "evaluation_time": "2026-04-15T10:00:00Z",
        "conditions": [],
        "medications": [],
        "risk_scores": {
            "ascvd_10yr": {"value": 8.5},
        },
    }
    query = _build_clinical_query(ctx)
    assert "8.5%" in query
    assert "cardiovascular risk reduction" in query


# --- Age computation ---


def test_compute_age():
    assert _compute_age("1970-06-15", "2026-04-15T10:00:00Z") == 55


def test_compute_age_before_birthday():
    assert _compute_age("1970-06-15", "2026-05-15T10:00:00Z") == 55


def test_compute_age_after_birthday():
    assert _compute_age("1970-06-15", "2026-07-15T10:00:00Z") == 56


def test_compute_age_invalid():
    assert _compute_age("not-a-date") is None


# --- Cosine similarity ---


def test_cosine_similarity_identical():
    vec = [1.0, 2.0, 3.0]
    assert abs(_cosine_similarity(vec, vec) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    assert abs(_cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-6


def test_cosine_similarity_zero_vector():
    assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
