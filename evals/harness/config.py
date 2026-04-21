"""Harness configuration: model versions, rubric settings, paths.

All model version strings are pinned in evals/rubric.md. This module
is the single Python source of truth for those values.
"""

from __future__ import annotations

from pathlib import Path

# Pinned model versions (must match evals/rubric.md)
ARM_MODEL = "claude-sonnet-4-20250514"
JUDGE_MODEL = "claude-opus-4-20250514"

# Temperature for all LLM calls
TEMPERATURE = 0

# Rubric version — bump when rubric dimensions or scoring criteria change
RUBRIC_VERSION = "v1.1"

# Arm B chunking parameters
CHUNK_STRATEGY = "section"
CHUNK_SIZE_TOKENS = 500  # only used as fallback for oversized sections
CHUNK_OVERLAP_TOKENS = 50  # only used as fallback for oversized sections
MAX_SECTION_TOKENS = 1000  # sections above this get token-based splitting
TOP_K_PER_QUERY = 3
MAX_UNIQUE_CHUNKS = 8
TOP_K_CHUNKS = 5  # kept for backwards compat; unused in section strategy
EMBEDDING_MODEL = "text-embedding-3-small"

# Paths
EVALS_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_ROOT = EVALS_ROOT / "fixtures"
RESULTS_ROOT = EVALS_ROOT / "results"
GUIDELINES_ROOT = EVALS_ROOT.parent / "docs" / "reference" / "guidelines"

# Arm IDs
ARM_IDS = ("a", "b", "c")

# System prompt shared across all three arms — only the context varies
SYSTEM_PROMPT = """\
You are a clinical decision support assistant. Given a patient's clinical \
context, provide a structured list of next-best-action recommendations.

For each action, provide:
- id: a short identifier
- label: human-readable action name
- rationale: brief clinical justification
- priority: integer (1 = highest priority)
- source: which guideline or evidence supports this action (if known)

Return your response as a JSON object with this schema:
{
  "actions": [
    {
      "id": "string",
      "label": "string",
      "rationale": "string",
      "priority": integer,
      "source": "string or null"
    }
  ],
  "reasoning": "brief narrative explaining your clinical reasoning"
}

Be specific and evidence-based. Do not recommend actions that are \
contraindicated for this patient. Prioritize by clinical impact.
"""
