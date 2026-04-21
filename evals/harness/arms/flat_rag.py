"""Arm B: PatientContext + section-level multi-query RAG from guideline prose.

Chunks are sourced from docs/reference/guidelines/*.md. Section-aware
splitting preserves ## headers as chunk boundaries. Multi-query retrieval
builds separate embedding queries per clinical concern (conditions,
medications, risk scores) and deduplicates results. Embedding model:
text-embedding-3-small via OpenAI API.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from openai import OpenAI

from harness.config import (
    ARM_MODEL,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
    EMBEDDING_MODEL,
    GUIDELINES_ROOT,
    MAX_SECTION_TOKENS,
    MAX_UNIQUE_CHUNKS,
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOP_K_PER_QUERY,
)


PROMPT_TEMPLATE = """\
Based on the following patient information and relevant clinical guideline \
excerpts, provide your clinical next-best-action recommendations.

## Patient Context

{patient_context}

## Relevant Guideline Excerpts

{guideline_chunks}

Respond with a JSON object containing your recommended actions.
"""


def _approximate_token_count(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


def _chunk_text_by_tokens(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by approximate token count.

    Fallback for sections that exceed MAX_SECTION_TOKENS.
    """
    paragraphs = re.split(r"\n\n+", text)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _approximate_token_count(para)

        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))

            overlap_tokens = 0
            overlap_start = len(current_chunk)
            for i in range(len(current_chunk) - 1, -1, -1):
                p_tokens = _approximate_token_count(current_chunk[i])
                if overlap_tokens + p_tokens > overlap:
                    break
                overlap_tokens += p_tokens
                overlap_start = i

            current_chunk = current_chunk[overlap_start:]
            current_tokens = sum(_approximate_token_count(p) for p in current_chunk)

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def _chunk_by_sections(text: str) -> list[str]:
    """Split markdown text on ## headers, preserving headers in each chunk.

    Each chunk is a complete section (header + body). Sections exceeding
    MAX_SECTION_TOKENS get split further via token-based chunking, with
    the header prepended to each sub-chunk.
    """
    # Split on ## headers (keep the header with the section that follows)
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)

    chunks: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        if _approximate_token_count(part) > MAX_SECTION_TOKENS:
            # Extract header for prepending to sub-chunks
            lines = part.split("\n", 1)
            header = lines[0] if lines[0].startswith("## ") else ""
            body = lines[1] if len(lines) > 1 else part

            sub_chunks = _chunk_text_by_tokens(
                body, CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS
            )
            for sc in sub_chunks:
                if header:
                    chunks.append(f"{header}\n\n{sc}")
                else:
                    chunks.append(sc)
        else:
            chunks.append(part)

    return chunks


# Files that describe cross-guideline relationships (edges removed pending
# clinician review). Excluding these keeps Arm B's source material aligned
# with the actual graph state — no preemption/modifier prose that the graph
# can't corroborate.
_EXCLUDED_FILES = {"cross-guideline-map.md", "preemption-map.md"}


def _load_guideline_texts() -> list[str]:
    """Load guideline markdown files from docs/reference/guidelines/.

    Excludes cross-guideline relationship docs whose corresponding graph
    edges have been removed pending clinician review.
    """
    texts: list[str] = []
    if GUIDELINES_ROOT.exists():
        for md_file in sorted(GUIDELINES_ROOT.glob("*.md")):
            if md_file.name in _EXCLUDED_FILES:
                continue
            texts.append(md_file.read_text())
    return texts


def _embed_texts(texts: list[str], api_key: str | None = None) -> list[list[float]]:
    """Embed a list of texts using OpenAI text-embedding-3-small."""
    client = OpenAI(api_key=api_key) if api_key else OpenAI()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _compute_age(dob_str: str, eval_time: str | None = None) -> int | None:
    """Compute age from date of birth string."""
    try:
        dob = date.fromisoformat(dob_str[:10])
        if eval_time:
            ref = datetime.fromisoformat(eval_time.replace("Z", "+00:00")).date()
        else:
            ref = date.today()
        age = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
        return age
    except (ValueError, TypeError):
        return None


def _build_clinical_query(patient_context: dict[str, Any]) -> str:
    """Build a clinically-framed query string from patient context.

    Instead of a flat list of demographics, constructs a natural-language
    clinical question that helps the embedding model match relevant
    guideline sections.
    """
    patient = patient_context.get("patient", {})
    age = _compute_age(
        patient.get("date_of_birth", ""),
        patient_context.get("evaluation_time"),
    )
    sex = patient.get("administrative_sex", "unknown")

    # Gather condition display names
    condition_names: list[str] = []
    for cond in patient_context.get("conditions", []):
        for code in cond.get("codes", []):
            display = code.get("display", code.get("code", ""))
            if display:
                condition_names.append(display)
                break  # one display per condition

    # Gather observation summaries
    obs_parts: list[str] = []
    for obs in patient_context.get("observations", []):
        display = ""
        for code in obs.get("codes", []):
            display = code.get("display", code.get("code", ""))
            if display:
                break
        value_obj = obs.get("value", {})
        if value_obj and isinstance(value_obj, dict):
            vq = value_obj.get("value_quantity", {})
            if vq:
                obs_parts.append(f"{display} {vq.get('value', '')} {vq.get('unit', '')}")

    # Risk scores
    risk_parts: list[str] = []
    risk_scores = patient_context.get("risk_scores", {})
    for name, score in risk_scores.items():
        val = score.get("value", "unknown")
        risk_parts.append(f"{name} {val}%")

    # Build the clinical query
    age_str = f"{age}-year-old" if age else "age-unknown"
    demographics = f"{age_str} {sex}"
    conditions_str = ", ".join(condition_names) if condition_names else "no active conditions"
    obs_str = ", ".join(obs_parts) if obs_parts else ""
    risk_str = ", ".join(risk_parts) if risk_parts else ""

    parts = [f"{demographics} with {conditions_str}"]
    if obs_str:
        parts[0] += f" ({obs_str})"
    if risk_str:
        parts.append(f"Risk scores: {risk_str}")

    # Clinical question framing
    concern_areas: list[str] = []
    for cn in condition_names:
        concern_areas.append(f"{cn} management")
    if risk_scores.get("ascvd_10yr"):
        concern_areas.append("cardiovascular risk reduction")
        concern_areas.append("statin therapy")

    if concern_areas:
        parts.append(
            f"What are the guideline recommendations for {', '.join(concern_areas)}?"
        )

    return ". ".join(parts)


def _build_per_concern_queries(patient_context: dict[str, Any]) -> list[str]:
    """Build separate embedding queries per clinical concern.

    One query per active condition, one per medication class, one for
    risk scores. Each query includes basic demographics for context.
    """
    patient = patient_context.get("patient", {})
    age = _compute_age(
        patient.get("date_of_birth", ""),
        patient_context.get("evaluation_time"),
    )
    sex = patient.get("administrative_sex", "unknown")
    age_str = f"{age}-year-old" if age else "age-unknown"
    demo = f"{age_str} {sex}"

    queries: list[str] = []

    # One query per condition
    for cond in patient_context.get("conditions", []):
        for code in cond.get("codes", []):
            display = code.get("display", code.get("code", ""))
            if display:
                queries.append(
                    f"{demo} with {display}. "
                    f"Guideline recommendations for {display} management and treatment."
                )
                break

    # One query per medication class
    med_classes_seen: set[str] = set()
    for med in patient_context.get("medications", []):
        for code in med.get("codes", []):
            display = code.get("display", code.get("code", ""))
            if display and display not in med_classes_seen:
                med_classes_seen.add(display)
                queries.append(
                    f"{demo} on {display}. "
                    f"Guideline recommendations for {display} dosing, monitoring, and contraindications."
                )
                break

    # One query for risk scores
    risk_scores = patient_context.get("risk_scores", {})
    if risk_scores:
        risk_parts = []
        for name, score in risk_scores.items():
            risk_parts.append(f"{name}: {score.get('value', 'unknown')}%")
        queries.append(
            f"{demo} with risk scores: {', '.join(risk_parts)}. "
            f"Guideline recommendations for cardiovascular risk reduction and preventive therapy."
        )

    # Always include the main clinical query as a catch-all
    queries.append(_build_clinical_query(patient_context))

    return queries


def retrieve_chunks(
    patient_context: dict[str, Any],
    openai_api_key: str | None = None,
) -> list[str]:
    """Retrieve relevant guideline chunks via multi-query section-level RAG.

    1. Load guideline prose and split into section-level chunks.
    2. Build per-concern queries from patient context.
    3. Embed all queries and chunks.
    4. For each query, retrieve top-k; deduplicate by chunk index.
    5. Return up to MAX_UNIQUE_CHUNKS unique chunks.
    """
    guideline_texts = _load_guideline_texts()
    if not guideline_texts:
        return []

    all_chunks: list[str] = []
    for text in guideline_texts:
        all_chunks.extend(_chunk_by_sections(text))

    if not all_chunks:
        return []

    queries = _build_per_concern_queries(patient_context)

    # Embed all queries and chunks in one batch
    all_texts = queries + all_chunks
    embeddings = _embed_texts(all_texts, api_key=openai_api_key)

    query_embeddings = embeddings[: len(queries)]
    chunk_embeddings = embeddings[len(queries) :]

    # Multi-query retrieval: top-k per query, deduplicate by chunk index
    seen_indices: set[int] = set()
    result_chunks: list[str] = []

    for q_emb in query_embeddings:
        scored = [
            (i, _cosine_similarity(q_emb, ce))
            for i, ce in enumerate(chunk_embeddings)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        for idx, _score in scored[:TOP_K_PER_QUERY]:
            if idx not in seen_indices:
                seen_indices.add(idx)
                result_chunks.append(all_chunks[idx])
                if len(result_chunks) >= MAX_UNIQUE_CHUNKS:
                    return result_chunks

    return result_chunks


def get_prompt(patient_context: dict[str, Any], chunks: list[str]) -> str:
    """Build the Arm B prompt with patient context and retrieved chunks."""
    pc_text = json.dumps(patient_context, indent=2)
    chunks_text = "\n\n---\n\n".join(
        f"[Excerpt {i + 1}]\n{chunk}" for i, chunk in enumerate(chunks)
    )
    return PROMPT_TEMPLATE.format(
        patient_context=pc_text,
        guideline_chunks=chunks_text,
    )


def run(
    patient_context: dict[str, Any],
    anthropic_api_key: str | None = None,
    openai_api_key: str | None = None,
) -> dict[str, Any]:
    """Execute Arm B: section-level multi-query RAG with guideline chunks.

    Returns the parsed JSON output from the model.
    """
    chunks = retrieve_chunks(patient_context, openai_api_key=openai_api_key)
    prompt = get_prompt(patient_context, chunks)

    client = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else Anthropic()

    response = client.messages.create(
        model=ARM_MODEL,
        max_tokens=2048,
        temperature=TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"actions": [], "reasoning": raw_text, "_parse_error": True}

    return {
        "arm": "b",
        "model": ARM_MODEL,
        "chunks_used": len(chunks),
        "raw_output": raw_text,
        "parsed": parsed,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
