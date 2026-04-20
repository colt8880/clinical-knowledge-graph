/**
 * Builds an ordered list of RecCardData from an EvalTrace.
 *
 * Ordering: guideline priority (descending) → evidence grade (higher wins) → rec id (deterministic).
 * Convergence: identifies shared clinical entities targeted by recs from ≥2 guidelines.
 */

import type { EvalTrace, TraceEvent, Recommendation } from "@/lib/eval/trace-nav";

// ── Guideline priority ─────────────────────────────────────────────
// Higher value = higher priority = sorts first.
// From v1-spec: ACC/AHA 200, KDIGO 200, USPSTF 100.
const GUIDELINE_PRIORITY: Record<string, number> = {
  "guideline:acc-aha-cholesterol-2018": 200,
  "guideline:kdigo-ckd-2024": 200,
  "guideline:uspstf-statin-2022": 100,
};

const DEFAULT_PRIORITY = 50;

// Evidence grade ordering: higher rank = sorts first.
const GRADE_RANK: Record<string, number> = {
  // USPSTF
  A: 100,
  B: 90,
  C: 70,
  D: 20,
  I: 50,
  // ACC/AHA: COR I / LOE A style — rank by COR
  "COR I": 100,
  "COR IIa": 85,
  "COR IIb": 70,
  "COR III": 30,
  // KDIGO
  "1A": 100,
  "1B": 90,
  "1C": 80,
  "1D": 70,
  "2A": 65,
  "2B": 60,
  "2C": 55,
  "2D": 50,
};

const DEFAULT_GRADE_RANK = 0;

// ── Domain labels ──────────────────────────────────────────────────
// Map guideline_id to short domain label for display.
const GUIDELINE_DOMAIN: Record<string, string> = {
  "guideline:uspstf-statin-2022": "USPSTF",
  "guideline:acc-aha-cholesterol-2018": "ACC_AHA",
  "guideline:kdigo-ckd-2024": "KDIGO",
};

// Short human-readable titles for guidelines.
const GUIDELINE_SHORT_TITLE: Record<string, string> = {
  "guideline:uspstf-statin-2022": "USPSTF 2022 Statin",
  "guideline:acc-aha-cholesterol-2018": "ACC/AHA 2018 Cholesterol",
  "guideline:kdigo-ckd-2024": "KDIGO 2024 CKD",
};

// ── Types ──────────────────────────────────────────────────────────

export interface ActionInfo {
  action_node_id: string;
  entity_type: string;
  satisfied: boolean;
}

export interface ConvergenceEntry {
  entity_id: string;
  entity_type: string;
  recommended_by: {
    rec_id: string;
    guideline: string;
    domain: string;
  }[];
}

export interface RecCardData {
  recommendation_id: string;
  guideline_id: string;
  domain: string;
  guideline_title: string;
  status: string;
  evidence_grade: string;
  reason: string;
  offered_strategies?: string[];
  satisfying_strategy?: string | null;
  preempted_by?: string | null;
  modifiers: Recommendation["modifiers"];
  /** Primary action summary derived from trace events. */
  action_summary: string;
  /** Actions from the trace for this rec's strategies. */
  actions: ActionInfo[];
  /** Convergence entries: other guidelines that target the same entities. */
  convergence: ConvergenceEntry[];
}

// ── Helpers ────────────────────────────────────────────────────────

function guidelinePriority(guidelineId: string): number {
  return GUIDELINE_PRIORITY[guidelineId] ?? DEFAULT_PRIORITY;
}

function gradeRank(grade: string): number {
  return GRADE_RANK[grade] ?? DEFAULT_GRADE_RANK;
}

export function getDomain(guidelineId: string): string {
  return GUIDELINE_DOMAIN[guidelineId] ?? "UNKNOWN";
}

export function getGuidelineTitle(guidelineId: string): string {
  return GUIDELINE_SHORT_TITLE[guidelineId] ?? guidelineId;
}

/**
 * Extract actions per recommendation from trace events.
 * Returns a map: rec_id → ActionInfo[].
 */
function extractActions(events: TraceEvent[]): Map<string, ActionInfo[]> {
  const recActions = new Map<string, ActionInfo[]>();
  for (const e of events) {
    if (e.type === "action_checked") {
      const list = recActions.get(e.recommendation_id) ?? [];
      list.push({
        action_node_id: e.action_node_id,
        entity_type: e.action_entity_type,
        satisfied: e.satisfied,
      });
      recActions.set(e.recommendation_id, list);
    }
  }
  return recActions;
}

/**
 * Derive a human-readable action summary from a rec's actions.
 */
function buildActionSummary(actions: ActionInfo[]): string {
  if (actions.length === 0) return "";
  const meds = actions.filter((a) => a.entity_type === "Medication");
  const procs = actions.filter((a) => a.entity_type === "Procedure");
  const obs = actions.filter((a) => a.entity_type === "Observation");

  const parts: string[] = [];
  if (meds.length > 0) {
    const names = meds.map((m) => formatEntityId(m.action_node_id));
    parts.push(
      meds.length === 1
        ? `Start ${names[0]}`
        : `Start one of: ${names.join(", ")}`,
    );
  }
  if (procs.length > 0) {
    parts.push(
      procs.map((p) => formatEntityId(p.action_node_id)).join(", "),
    );
  }
  if (obs.length > 0) {
    parts.push(
      obs.map((o) => formatEntityId(o.action_node_id)).join(", "),
    );
  }
  return parts.join("; ");
}

/** Turn "med:atorvastatin" → "Atorvastatin" */
function formatEntityId(id: string): string {
  const name = id.includes(":") ? id.split(":").slice(1).join(":") : id;
  return name
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * Detect convergence: shared clinical entities targeted by recs from ≥2 guidelines.
 * Returns a map: entity_id → ConvergenceEntry.
 */
function detectConvergence(
  recommendations: Recommendation[],
  recActionsMap: Map<string, ActionInfo[]>,
): Map<string, ConvergenceEntry> {
  // entity_id → set of { rec_id, guideline_id }
  const entityToRecs = new Map<
    string,
    { rec_id: string; guideline_id: string }[]
  >();

  for (const rec of recommendations) {
    // Skip preempted recs — they're suppressed, not active convergence
    if (rec.preempted_by) continue;

    const actions = recActionsMap.get(rec.recommendation_id) ?? [];
    for (const action of actions) {
      const list = entityToRecs.get(action.action_node_id) ?? [];
      // Avoid duplicates (same rec might check same entity twice)
      if (!list.some((e) => e.rec_id === rec.recommendation_id)) {
        list.push({
          rec_id: rec.recommendation_id,
          guideline_id: rec.guideline_id,
        });
      }
      entityToRecs.set(action.action_node_id, list);
    }
  }

  // Only keep entities targeted by ≥2 different guidelines
  const convergence = new Map<string, ConvergenceEntry>();
  const entityEntries = Array.from(entityToRecs.entries());
  for (const pair of entityEntries) {
    const entityId = pair[0];
    const recs = pair[1];
    const guidelineIds = recs.map(
      (r: { rec_id: string; guideline_id: string }) => r.guideline_id,
    );
    const guidelines = new Set(guidelineIds);
    if (guidelines.size >= 2) {
      // Find entity type from any rec's actions
      let entityType = "Entity";
      for (const r of recs) {
        const actions = recActionsMap.get(r.rec_id) ?? [];
        const match = actions.find(
          (a: ActionInfo) => a.action_node_id === entityId,
        );
        if (match) {
          entityType = match.entity_type;
          break;
        }
      }

      convergence.set(entityId, {
        entity_id: entityId,
        entity_type: entityType,
        recommended_by: recs.map(
          (r: { rec_id: string; guideline_id: string }) => ({
            rec_id: r.rec_id,
            guideline: getGuidelineTitle(r.guideline_id),
            domain: getDomain(r.guideline_id),
          }),
        ),
      });
    }
  }

  return convergence;
}

// ── Main builder ───────────────────────────────────────────────────

export function buildRecList(trace: EvalTrace): RecCardData[] {
  const { recommendations, events } = trace;
  if (recommendations.length === 0) return [];

  const recActionsMap = extractActions(events);
  const convergenceMap = detectConvergence(recommendations, recActionsMap);

  const cards: RecCardData[] = recommendations.map((rec) => {
    const actions = recActionsMap.get(rec.recommendation_id) ?? [];

    // Find convergence entries relevant to this rec
    const recConvergence: ConvergenceEntry[] = [];
    const convergenceEntries = Array.from(convergenceMap.values());
    for (const entry of convergenceEntries) {
      if (
        entry.recommended_by.some(
          (r: ConvergenceEntry["recommended_by"][number]) =>
            r.rec_id === rec.recommendation_id,
        )
      ) {
        recConvergence.push(entry);
      }
    }

    return {
      recommendation_id: rec.recommendation_id,
      guideline_id: rec.guideline_id,
      domain: getDomain(rec.guideline_id),
      guideline_title: getGuidelineTitle(rec.guideline_id),
      status: rec.status,
      evidence_grade: rec.evidence_grade,
      reason: rec.reason,
      offered_strategies: rec.offered_strategies,
      satisfying_strategy: rec.satisfying_strategy,
      preempted_by: rec.preempted_by,
      modifiers: rec.modifiers,
      action_summary: buildActionSummary(actions),
      actions,
      convergence: recConvergence,
    };
  });

  // Sort: guideline priority desc → grade rank desc → rec id asc
  cards.sort((a, b) => {
    const pA = guidelinePriority(a.guideline_id);
    const pB = guidelinePriority(b.guideline_id);
    if (pA !== pB) return pB - pA;

    const gA = gradeRank(a.evidence_grade);
    const gB = gradeRank(b.evidence_grade);
    if (gA !== gB) return gB - gA;

    return a.recommendation_id.localeCompare(b.recommendation_id);
  });

  return cards;
}
