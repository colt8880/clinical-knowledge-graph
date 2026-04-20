"use client";

import { useCallback, useRef } from "react";
import type { InteractionsResponse } from "@/lib/api/client";
import type { EdgeTypeFilter } from "@/lib/interactions/collapse";
import { countEdges, guidelinePairs } from "@/lib/interactions/collapse";

interface InteractionsLegendProps {
  data: InteractionsResponse;
  edgeTypeFilter: EdgeTypeFilter;
  onEdgeTypeChange: (filter: EdgeTypeFilter) => void;
  excludedPairs: Set<string>;
  onTogglePair: (pairKey: string) => void;
}

const EDGE_TYPE_OPTIONS: { value: EdgeTypeFilter; label: string }[] = [
  { value: "both", label: "Both" },
  { value: "preemption", label: "Preemptions" },
  { value: "modifier", label: "Modifiers" },
];

export default function InteractionsLegend({
  data,
  edgeTypeFilter,
  onEdgeTypeChange,
  excludedPairs,
  onTogglePair,
}: InteractionsLegendProps) {
  const counts = countEdges(data);
  const pairs = guidelinePairs(data);
  const chipRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleChipKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        const next = (index + 1) % pairs.length;
        chipRefs.current[next]?.focus();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        const prev = (index - 1 + pairs.length) % pairs.length;
        chipRefs.current[prev]?.focus();
      }
    },
    [pairs.length],
  );

  return (
    <div className="flex flex-col gap-4 p-4 w-64 border-r border-slate-200 bg-slate-50 overflow-y-auto" data-testid="interactions-legend">
      {/* Edge type filter */}
      <section>
        <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
          Edge Type
        </h3>
        <div className="flex flex-col gap-1" role="radiogroup" aria-label="Edge type filter">
          {EDGE_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              role="radio"
              aria-checked={edgeTypeFilter === opt.value}
              onClick={() => onEdgeTypeChange(opt.value)}
              className={`px-3 py-1.5 rounded text-xs font-medium text-left transition-colors ${
                edgeTypeFilter === opt.value
                  ? "bg-slate-200 text-slate-900"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
              data-testid={`edge-type-${opt.value}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </section>

      {/* Guideline-pair filter */}
      {pairs.length > 0 && (
        <section>
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Guideline Pairs
          </h3>
          <div className="flex flex-col gap-1" role="group" aria-label="Guideline pair filter">
            {pairs.map((pair, i) => {
              const key = pair.domains.join(":");
              const active = !excludedPairs.has(key);
              return (
                <button
                  key={key}
                  ref={(el) => { chipRefs.current[i] = el; }}
                  role="checkbox"
                  aria-checked={active}
                  onClick={() => onTogglePair(key)}
                  onKeyDown={(e) => handleChipKeyDown(e, i)}
                  className={`px-3 py-1.5 rounded text-xs font-medium text-left transition-colors ${
                    active
                      ? "bg-slate-200 text-slate-900"
                      : "bg-slate-50 text-slate-400 line-through"
                  }`}
                  data-testid={`pair-chip-${key}`}
                >
                  {pair.label}
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* Legend */}
      <section>
        <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
          Legend
        </h3>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-0 border-t-[3px] border-[#991b1b]" />
            <span className="text-xs text-slate-700">PREEMPTED_BY</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0 border-t-2 border-dashed border-[#d97706]" />
            <span className="text-xs text-slate-700">MODIFIES</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0 border-t-2 border-dashed border-[#d97706] opacity-50" />
            <span className="text-xs text-slate-700">MODIFIES (suppressed)</span>
          </div>
        </div>
      </section>

      {/* Summary counts */}
      <section>
        <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
          Summary
        </h3>
        <p className="text-xs text-slate-600" data-testid="interactions-summary">
          {counts.preemptions} preemption{counts.preemptions !== 1 ? "s" : ""}
          {" · "}
          {counts.modifiers} modifier{counts.modifiers !== 1 ? "s" : ""}
          {counts.sharedEntities > 0 && (
            <>
              {" · "}
              {counts.sharedEntities} shared entit{counts.sharedEntities !== 1 ? "ies" : "y"}
            </>
          )}
        </p>
      </section>
    </div>
  );
}
