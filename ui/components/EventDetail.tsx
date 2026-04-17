"use client";

import type { TraceEvent, InputRead } from "@/lib/eval/trace-nav";
import { eventTypeLabel } from "@/lib/eval/trace-nav";

function InputReadTable({ inputs }: { inputs: InputRead[] }) {
  if (inputs.length === 0) return null;

  return (
    <div className="mt-3">
      <h4 className="text-[10px] uppercase tracking-wide font-semibold text-slate-500 mb-1">
        Inputs Read
      </h4>
      <table className="w-full text-xs border border-slate-200 rounded">
        <thead>
          <tr className="bg-slate-50">
            <th className="text-left px-2 py-1 font-semibold text-slate-500">Source</th>
            <th className="text-left px-2 py-1 font-semibold text-slate-500">Locator</th>
            <th className="text-left px-2 py-1 font-semibold text-slate-500">Value</th>
            <th className="text-left px-2 py-1 font-semibold text-slate-500">Present</th>
          </tr>
        </thead>
        <tbody>
          {inputs.map((ir, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="px-2 py-1 font-mono text-[10px]">{ir.source}</td>
              <td className="px-2 py-1 font-mono text-[10px]">{ir.locator}</td>
              <td className="px-2 py-1 font-mono text-[10px] max-w-[150px] truncate">
                {ir.value !== undefined ? JSON.stringify(ir.value) : "—"}
              </td>
              <td className="px-2 py-1">
                {ir.present ? (
                  <span className="text-green-600">yes</span>
                ) : (
                  <span className="text-red-500">no</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PredicateDetail({ event }: { event: TraceEvent & { type: "predicate_evaluated" } }) {
  return (
    <>
      <Field label="Predicate" value={event.predicate} mono />
      <Field label="Path" value={event.path.join(" → ")} mono />
      <Field label="Result" value={event.result} badge badgeColor={resultColor(event.result)} />
      {event.missing_data_policy_applied && (
        <Field label="Missing Data Policy" value={event.missing_data_policy_applied} />
      )}
      {event.note && <Field label="Note" value={event.note} />}
      <div className="mt-2">
        <h4 className="text-[10px] uppercase tracking-wide font-semibold text-slate-500 mb-1">
          Args
        </h4>
        <pre className="bg-slate-50 border border-slate-200 rounded p-2 text-[10px] font-mono overflow-x-auto">
          {JSON.stringify(event.args, null, 2)}
        </pre>
      </div>
      <InputReadTable inputs={event.inputs_read} />
    </>
  );
}

function RiskScoreDetail({ event }: { event: TraceEvent & { type: "risk_score_lookup" } }) {
  return (
    <>
      <Field label="Score" value={event.score_name} mono />
      <Field label="Resolution" value={event.resolution} />
      {event.supplied_value != null && (
        <Field label="Supplied Value" value={String(event.supplied_value)} />
      )}
      {event.computed_value != null && (
        <Field label="Computed Value" value={String(event.computed_value)} />
      )}
      {event.method && <Field label="Method" value={event.method} mono />}
      {event.note && <Field label="Note" value={event.note} />}
      {event.inputs_read && <InputReadTable inputs={event.inputs_read} />}
    </>
  );
}

function resultColor(result: string): string {
  if (result === "true") return "bg-green-100 text-green-700";
  if (result === "false") return "bg-red-100 text-red-700";
  return "bg-slate-100 text-slate-600";
}

function Field({
  label,
  value,
  mono,
  badge,
  badgeColor,
}: {
  label: string;
  value: string;
  mono?: boolean;
  badge?: boolean;
  badgeColor?: string;
}) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-[10px] uppercase tracking-wide font-semibold text-slate-400 w-28 shrink-0 pt-0.5">
        {label}
      </span>
      {badge ? (
        <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${badgeColor}`}>
          {value}
        </span>
      ) : (
        <span className={`text-xs text-slate-800 ${mono ? "font-mono" : ""}`}>
          {value}
        </span>
      )}
    </div>
  );
}

interface EventDetailProps {
  event: TraceEvent | null;
}

export default function EventDetail({ event }: EventDetailProps) {
  if (!event) {
    return (
      <div className="text-slate-400 italic text-sm px-5 pt-10 text-center">
        Run a fixture to see trace events.
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto h-full" data-testid="event-detail">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-mono text-slate-400">seq {event.seq}</span>
        <span className="text-xs font-semibold text-slate-700">
          {eventTypeLabel(event.type)}
        </span>
      </div>

      {event.type === "evaluation_started" && (
        <>
          <Field label="Age" value={`${event.patient_age_years}`} />
          <Field label="Sex" value={event.patient_sex} />
          <Field label="Guidelines" value={event.guidelines_in_scope.join(", ")} />
        </>
      )}

      {event.type === "guideline_entered" && (
        <>
          <Field label="Guideline" value={event.guideline_title} />
          <Field label="ID" value={event.guideline_id} mono />
        </>
      )}

      {event.type === "recommendation_considered" && (
        <>
          <Field label="Recommendation" value={event.recommendation_title} />
          <Field label="ID" value={event.recommendation_id} mono />
          <Field label="Grade" value={event.evidence_grade} />
          <Field label="Intent" value={event.intent} />
          <Field label="Trigger" value={event.trigger} />
        </>
      )}

      {event.type === "eligibility_evaluation_started" && (
        <Field label="Recommendation" value={event.recommendation_id} mono />
      )}

      {event.type === "predicate_evaluated" && <PredicateDetail event={event} />}

      {event.type === "composite_resolved" && (
        <>
          <Field label="Operator" value={event.operator} mono />
          <Field label="Path" value={event.path.join(" → ")} mono />
          <Field label="Result" value={event.result} badge badgeColor={resultColor(event.result)} />
          <Field label="Short-circuited" value={event.short_circuited ? "yes" : "no"} />
        </>
      )}

      {event.type === "eligibility_evaluation_completed" && (
        <>
          <Field label="Recommendation" value={event.recommendation_id} mono />
          <Field label="Result" value={event.result} badge badgeColor={
            event.result === "eligible" ? "bg-green-100 text-green-700" :
            event.result === "ineligible" ? "bg-red-100 text-red-700" :
            "bg-slate-100 text-slate-600"
          } />
          <Field label="Final Value" value={event.final_value} />
        </>
      )}

      {event.type === "strategy_considered" && (
        <>
          <Field label="Strategy" value={event.strategy_name} />
          <Field label="ID" value={event.strategy_id} mono />
          <Field label="Recommendation" value={event.recommendation_id} mono />
        </>
      )}

      {event.type === "action_checked" && (
        <>
          <Field label="Action" value={event.action_node_id} mono />
          <Field label="Entity Type" value={event.action_entity_type} />
          <Field label="Satisfied" value={event.satisfied ? "yes" : "no"} badge badgeColor={
            event.satisfied ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          } />
          {event.cadence && <Field label="Cadence" value={event.cadence} />}
          {event.lookback && <Field label="Lookback" value={event.lookback} />}
          {event.note && <Field label="Note" value={event.note} />}
          <InputReadTable inputs={event.inputs_read} />
        </>
      )}

      {event.type === "strategy_resolved" && (
        <>
          <Field label="Strategy" value={event.strategy_id} mono />
          <Field label="Satisfied" value={event.satisfied ? "yes" : "no"} badge badgeColor={
            event.satisfied ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          } />
        </>
      )}

      {event.type === "risk_score_lookup" && <RiskScoreDetail event={event} />}

      {event.type === "exit_condition_triggered" && (
        <>
          <Field label="Exit" value={event.exit} mono />
          <Field label="Rationale" value={event.rationale} />
          <Field label="Recommendation" value={event.recommendation_id} mono />
        </>
      )}

      {event.type === "recommendation_emitted" && (
        <>
          <Field label="Recommendation" value={event.recommendation_id} mono />
          <Field label="Status" value={event.status} badge badgeColor={
            event.status === "due" ? "bg-blue-100 text-blue-700" :
            event.status === "up_to_date" ? "bg-green-100 text-green-700" :
            "bg-slate-100 text-slate-600"
          } />
          <Field label="Grade" value={event.evidence_grade} />
          <Field label="Reason" value={event.reason} />
          {event.offered_strategies && event.offered_strategies.length > 0 && (
            <Field label="Strategies" value={event.offered_strategies.join(", ")} mono />
          )}
        </>
      )}

      {event.type === "evaluation_completed" && (
        <>
          <Field label="Recs Emitted" value={String(event.recommendations_emitted)} />
          <Field label="Duration" value={`${event.duration_ms}ms`} />
        </>
      )}

      {event.type === "guideline_exited" && (
        <>
          <Field label="Guideline" value={event.guideline_id} mono />
          <Field label="Recs Emitted" value={String(event.recommendations_emitted)} />
        </>
      )}

      {event.type === "preemption_resolved" && (
        <>
          <Field label="Preempted Rec" value={event.preempted_recommendation_id} mono />
          <Field label="Winner Rec" value={event.preempting_recommendation_id} mono />
          <Field label="Edge Priority" value={String(event.edge_priority)} />
          <Field label="Reason" value={event.reason} />
        </>
      )}

      {event.type === "cross_guideline_match" && (
        <>
          <Field label="Source Rec" value={event.source_rec_id} mono />
          <Field label="Target Rec" value={event.target_rec_id} mono />
          <Field label="Nature" value={event.nature} badge badgeColor="bg-orange-100 text-orange-700" />
          <Field label="Note" value={event.note} />
          <Field label="Source Guideline" value={event.source_guideline_id} mono />
          <Field label="Target Guideline" value={event.target_guideline_id} mono />
        </>
      )}

      {/* Full payload for reference */}
      <details className="mt-4">
        <summary className="text-[10px] uppercase tracking-wide font-semibold text-slate-400 cursor-pointer">
          Raw payload
        </summary>
        <pre className="mt-1 bg-slate-50 border border-slate-200 rounded p-2 text-[10px] font-mono overflow-x-auto max-h-60 overflow-y-auto">
          {JSON.stringify(event, null, 2)}
        </pre>
      </details>
    </div>
  );
}
