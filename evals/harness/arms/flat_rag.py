"""Arm B: PatientContext + top-k chunks from guideline prose (flat RAG).

Chunks are sourced from docs/reference/guidelines/*.md. Retrieval uses
text-embedding-3-small via OpenAI API. Top-k=5 chunks at 500 tokens
with 50-token overlap.
"""

from __future__ import annotations

import json
import re
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
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOP_K_CHUNKS,
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


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by approximate token count.

    Splits on paragraph boundaries (double newline) first, then
    accumulates paragraphs into chunks of approximately chunk_size tokens.
    """
    paragraphs = re.split(r"\n\n+", text)
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _approximate_token_count(para)

        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))

            # Keep overlap: walk backwards to find paragraphs within overlap window
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


def retrieve_chunks(
    patient_context: dict[str, Any],
    openai_api_key: str | None = None,
) -> list[str]:
    """Retrieve the top-k most relevant guideline chunks for a patient context.

    1. Load and chunk all guideline prose.
    2. Build a query from patient demographics/conditions.
    3. Embed query and chunks.
    4. Return top-k by cosine similarity.
    """
    guideline_texts = _load_guideline_texts()
    if not guideline_texts:
        return []

    all_chunks: list[str] = []
    for text in guideline_texts:
        all_chunks.extend(
            _chunk_text(text, CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS)
        )

    if not all_chunks:
        return []

    # Build a query string from patient context
    query_parts: list[str] = []
    patient = patient_context.get("patient", {})
    query_parts.append(f"Age: computed from DOB {patient.get('date_of_birth', 'unknown')}")
    query_parts.append(f"Sex: {patient.get('administrative_sex', 'unknown')}")

    for cond in patient_context.get("conditions", []):
        for code in cond.get("codes", []):
            display = code.get("display", code.get("code", ""))
            query_parts.append(f"Condition: {display}")

    for med in patient_context.get("medications", []):
        for code in med.get("codes", []):
            display = code.get("display", code.get("code", ""))
            query_parts.append(f"Medication: {display}")

    risk_scores = patient_context.get("risk_scores", {})
    for name, score in risk_scores.items():
        query_parts.append(f"Risk score {name}: {score.get('value', 'unknown')}%")

    query = "\n".join(query_parts)

    # Embed query and chunks
    all_texts = [query] + all_chunks
    embeddings = _embed_texts(all_texts, api_key=openai_api_key)

    query_embedding = embeddings[0]
    chunk_embeddings = embeddings[1:]

    # Rank by similarity and return top-k
    scored = [
        (i, _cosine_similarity(query_embedding, ce))
        for i, ce in enumerate(chunk_embeddings)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    top_k = scored[:TOP_K_CHUNKS]
    return [all_chunks[i] for i, _ in top_k]


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
    """Execute Arm B: flat RAG with top-k guideline chunks.

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
