/**
 * Pure trace navigation state.
 *
 * The stepper is a pure function of (trace, currentIndex).
 * No hidden state — one source of truth for currentIndex drives
 * both the event list highlight and the graph node highlight.
 */

import type { components } from "@/lib/api/schema";

export type EvalTrace = components["schemas"]["eval-trace.schema"];
export type TraceEvent = components["schemas"]["Event"];
export type Recommendation = components["schemas"]["Recommendation"];
export type InputRead = components["schemas"]["InputRead"];

/** Extract the node ID(s) that should be highlighted for a given event. */
export function highlightedNodeIds(event: TraceEvent): string[] {
  switch (event.type) {
    case "evaluation_started":
    case "evaluation_completed":
      return [];

    case "guideline_entered":
      return [event.guideline_id];

    case "recommendation_considered":
    case "eligibility_evaluation_started":
    case "eligibility_evaluation_completed":
      return [event.recommendation_id];

    case "predicate_evaluated":
      return [event.recommendation_id];

    case "composite_resolved":
      return [event.recommendation_id];

    case "strategy_considered":
      return [event.strategy_id];

    case "action_checked":
      return [event.action_node_id];

    case "strategy_resolved":
      return [event.strategy_id];

    case "risk_score_lookup":
      return [];

    case "exit_condition_triggered":
      return [event.recommendation_id];

    case "recommendation_emitted":
      return [event.recommendation_id];

    default:
      return [];
  }
}

/** Return the convenience recommendations array from the trace envelope. */
export function deriveRecommendations(trace: EvalTrace): Recommendation[] {
  return trace.recommendations;
}

/** Human-readable label for an event type. */
export function eventTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    evaluation_started: "Evaluation Started",
    guideline_entered: "Guideline Entered",
    recommendation_considered: "Recommendation Considered",
    eligibility_evaluation_started: "Eligibility Evaluation Started",
    predicate_evaluated: "Predicate Evaluated",
    composite_resolved: "Composite Resolved",
    eligibility_evaluation_completed: "Eligibility Evaluation Completed",
    strategy_considered: "Strategy Considered",
    action_checked: "Action Checked",
    strategy_resolved: "Strategy Resolved",
    risk_score_lookup: "Risk Score Lookup",
    exit_condition_triggered: "Exit Condition Triggered",
    recommendation_emitted: "Recommendation Emitted",
    evaluation_completed: "Evaluation Completed",
  };
  return labels[type] ?? type;
}

/** Short summary line for an event (for the event list). */
export function eventSummary(event: TraceEvent): string {
  switch (event.type) {
    case "evaluation_started":
      return `${event.patient_age_years}${event.patient_sex === "male" ? "M" : "F"}`;

    case "guideline_entered":
      return event.guideline_title;

    case "recommendation_considered":
      return `${event.recommendation_title} (Grade ${event.evidence_grade})`;

    case "eligibility_evaluation_started":
      return event.recommendation_id;

    case "predicate_evaluated":
      return `${event.predicate} → ${event.result}`;

    case "composite_resolved":
      return `${event.operator} → ${event.result}${event.short_circuited ? " (short-circuited)" : ""}`;

    case "eligibility_evaluation_completed":
      return `${event.result} (${event.final_value})`;

    case "strategy_considered":
      return event.strategy_name;

    case "action_checked":
      return `${event.action_node_id} → ${event.satisfied ? "satisfied" : "not satisfied"}`;

    case "strategy_resolved":
      return `${event.strategy_id} → ${event.satisfied ? "satisfied" : "not satisfied"}`;

    case "risk_score_lookup":
      return `${event.score_name}: ${event.resolution}${event.supplied_value != null ? ` (${event.supplied_value})` : ""}`;

    case "exit_condition_triggered":
      return event.exit;

    case "recommendation_emitted":
      return `${event.recommendation_id} → ${event.status}`;

    case "evaluation_completed":
      return `${event.recommendations_emitted} recs in ${event.duration_ms}ms`;

    default:
      return "";
  }
}

/** Clamp an index to valid event range. */
export function clampIndex(index: number, eventCount: number): number {
  if (eventCount === 0) return 0;
  return Math.max(0, Math.min(index, eventCount - 1));
}
