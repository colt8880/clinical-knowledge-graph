"use client";

import { useCallback, useRef } from "react";
import type { InteractionsResponse } from "@/lib/api/client";
import type { EdgeTypeFilter } from "@/lib/interactions/collapse";
import { countEdges } from "@/lib/interactions/collapse";

interface InteractionsLegendProps {
  data: InteractionsResponse;
  edgeTypeFilter: EdgeTypeFilter;
  onEdgeTypeChange: (filter: EdgeTypeFilter) => void;
  selectedGuidelines: Set<string>;
  onToggleGuideline: (domain: string) => void;
}

const EDGE_TYPE_OPTIONS: { value: EdgeTypeFilter; label: string }[] = [
  { value: "both", label: "Both" },
  { value: "preemption", label: "Preemptions" },
  { value: "modifier", label: "Modifiers" },
];

const GUIDELINE_CHIPS: { domain: string; label: string; activeClass: string; color: string }[] = [
  { domain: "USPSTF", label: "USPSTF", activeClass: "bg-blue-100 text-blue-800 border-blue-400", color: "border-blue-400" },
  { domain: "ACC/AHA", label: "ACC/AHA", activeClass: "bg-purple-100 text-purple-800 border-purple-400", color: "border-purple-400" },
  { domain: "KDIGO", label: "KDIGO", activeClass: "bg-emerald-100 text-emerald-800 border-emerald-400", color: "border-emerald-400" },
  { domain: "ADA", label: "ADA", activeClass: "bg-amber-100 text-amber-800 border-amber-400", color: "border-amber-400" },
];

export default function InteractionsLegend({
  data,
  edgeTypeFilter,
  onEdgeTypeChange,
  selectedGuidelines,
  onToggleGuideline,
}: InteractionsLegendProps) {
  const hasSelection = selectedGuidelines.size >= 2;

  // Count edges only for selected guidelines.
  const filteredCounts = hasSelection
    ? countEdges({
        ...data,
        edges: data.edges.filter((edge) => {
          const sourceRec = data.recommendations.find((r) => r.id === edge.source);
          const targetRec = data.recommendations.find((r) => r.id === edge.target);
          return (
            sourceRec?.domain != null &&
            targetRec?.domain != null &&
            selectedGuidelines.has(sourceRec.domain) &&
            selectedGuidelines.has(targetRec.domain)
          );
        }),
      })
    : null;

  const chipRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleChipKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        const next = (index + 1) % GUIDELINE_CHIPS.length;
        chipRefs.current[next]?.focus();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        const prev = (index - 1 + GUIDELINE_CHIPS.length) % GUIDELINE_CHIPS.length;
        chipRefs.current[prev]?.focus();
      }
    },
    [],
  );

  return (
    <div className="flex flex-col gap-4 p-4 w-64 border-r border-slate-200 bg-slate-50 overflow-y-auto" data-testid="interactions-legend">
      {/* Guideline picker — always visible */}
      <section>
        <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
          Compare Guidelines
        </h3>
        <p className="text-[11px] text-slate-400 mb-2">
          Select two or more to view cross-guideline interactions.
        </p>
        <div className="flex flex-col gap-1.5" role="group" aria-label="Guideline selection">
          {GUIDELINE_CHIPS.map((chip, i) => {
            const active = selectedGuidelines.has(chip.domain);
            return (
              <button
                key={chip.domain}
                ref={(el) => { chipRefs.current[i] = el; }}
                role="checkbox"
                aria-checked={active}
                onClick={() => onToggleGuideline(chip.domain)}
                onKeyDown={(e) => handleChipKeyDown(e, i)}
                className={`px-3 py-2 rounded-lg text-xs font-semibold border-2 transition-colors cursor-pointer select-none ${
                  active
                    ? chip.activeClass
                    : `bg-white text-slate-400 ${chip.color} opacity-50`
                }`}
                data-testid={`guideline-chip-${chip.domain}`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </section>

      {/* Everything below only shows after 2+ guidelines selected */}
      {hasSelection && (
        <>
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
          {filteredCounts && (
            <section>
              <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
                Summary
              </h3>
              <p className="text-xs text-slate-600" data-testid="interactions-summary">
                {filteredCounts.preemptions} preemption{filteredCounts.preemptions !== 1 ? "s" : ""}
                {" · "}
                {filteredCounts.modifiers} modifier{filteredCounts.modifiers !== 1 ? "s" : ""}
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}
