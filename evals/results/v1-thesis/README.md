# v1 Thesis Run

**Commit:** `2168d56`
**Run name:** v1-thesis
**Rubric:** v1.1
**Judge runs:** 2 (self-consistency)

## Result

**THESIS GATE: PASS**

The graph-context arm (Arm C) outperforms flat RAG (Arm B) on multi-guideline fixtures by 0.59 composite points (threshold: ≥ 0.5). The convergence summary — surfacing that multiple guidelines independently recommend the same therapeutic actions via shared clinical entities — provides the LLM with structural information that flat text retrieval cannot replicate.

## Setup

- **Fixtures:** 16 total (12 single-guideline, 4 multi-guideline)
- **Arms:** A (vanilla LLM), B (flat RAG), C (graph context + convergence)
- **Arm model:** claude-sonnet-4-6-20250514
- **Judge model:** claude-opus-4-6-20250610
- **Temperature:** 0 (all calls)
- **Self-consistency:** 3 judge runs per fixture/arm

## Interpretation

Convergence visibility is a genuine graph capability that flat RAG cannot replicate. When multiple guidelines independently point at the same medication node, the graph surfaces this structural agreement explicitly. The LLM anchors on this multi-source evidence to produce better-integrated recommendations.

This does not mean the graph's value is limited to convergence. When clinician-reviewed cross-guideline edges (PREEMPTED_BY, MODIFIES) return, a follow-up thesis run can measure the incremental value of edge-based conflict resolution on top of convergence.

## Files

- `scorecard.md` — full scorecard with per-fixture breakdowns
- `scorecard.json` — machine-readable scorecard
- `README.md` — this file
