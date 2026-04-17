"use client";

import { useEffect, useRef } from "react";
import type { TraceEvent } from "@/lib/eval/trace-nav";
import { eventTypeLabel, eventSummary } from "@/lib/eval/trace-nav";

const EVENT_TYPE_COLORS: Record<string, string> = {
  evaluation_started: "bg-slate-100 text-slate-700",
  guideline_entered: "bg-purple-50 text-purple-700",
  recommendation_considered: "bg-blue-50 text-blue-700",
  eligibility_evaluation_started: "bg-blue-50 text-blue-600",
  predicate_evaluated: "bg-indigo-50 text-indigo-700",
  composite_resolved: "bg-indigo-50 text-indigo-600",
  eligibility_evaluation_completed: "bg-blue-50 text-blue-700",
  strategy_considered: "bg-amber-50 text-amber-700",
  action_checked: "bg-amber-50 text-amber-600",
  strategy_resolved: "bg-amber-50 text-amber-700",
  risk_score_lookup: "bg-cyan-50 text-cyan-700",
  exit_condition_triggered: "bg-red-50 text-red-700",
  recommendation_emitted: "bg-green-50 text-green-700",
  evaluation_completed: "bg-slate-100 text-slate-700",
  guideline_exited: "bg-purple-50 text-purple-600",
  preemption_resolved: "bg-red-50 text-red-700",
  cross_guideline_match: "bg-orange-50 text-orange-700",
};

interface TraceEventListProps {
  events: TraceEvent[];
  currentIndex: number;
  onSelectIndex: (index: number) => void;
}

export default function TraceEventList({
  events,
  currentIndex,
  onSelectIndex,
}: TraceEventListProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  // Scroll the active event into view when the index changes.
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [currentIndex]);

  return (
    <div
      ref={listRef}
      className="overflow-y-auto h-full"
      data-testid="trace-event-list"
    >
      {events.map((event, i) => {
        const isActive = i === currentIndex;
        const colors =
          EVENT_TYPE_COLORS[event.type] ?? "bg-slate-50 text-slate-600";

        return (
          <button
            key={event.seq}
            ref={isActive ? activeRef : undefined}
            className={`w-full text-left px-3 py-2 border-b border-slate-100 transition-colors ${
              isActive
                ? "bg-blue-100 border-l-4 border-l-blue-500"
                : "hover:bg-slate-50 border-l-4 border-l-transparent"
            }`}
            onClick={() => onSelectIndex(i)}
            data-testid={isActive ? "active-event" : undefined}
          >
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[10px] font-mono text-slate-400 w-6 shrink-0 text-right">
                {event.seq}
              </span>
              <span
                className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${colors}`}
              >
                {eventTypeLabel(event.type)}
              </span>
            </div>
            <div className="text-xs text-slate-600 pl-8 truncate">
              {eventSummary(event)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
