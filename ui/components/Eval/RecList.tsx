"use client";

import { useState, useCallback, useMemo } from "react";
import type { EvalTrace } from "@/lib/eval/trace-nav";
import { buildRecList } from "@/lib/recListBuilder";
import RecCard from "./RecCard";

interface RecListProps {
  trace: EvalTrace;
}

export default function RecList({ trace }: RecListProps) {
  const cards = useMemo(() => buildRecList(trace), [trace]);
  const [highlightedRecIds, setHighlightedRecIds] = useState<Set<string>>(
    new Set(),
  );

  const handleConvergenceClick = useCallback((relatedRecIds: string[]) => {
    setHighlightedRecIds((prev) => {
      // Toggle: if already highlighting these, clear; otherwise set.
      const same =
        prev.size === relatedRecIds.length &&
        relatedRecIds.every((id) => prev.has(id));
      return same ? new Set() : new Set(relatedRecIds);
    });
  }, []);

  if (cards.length === 0) {
    return (
      <div
        className="px-4 py-3 bg-slate-50 border-t border-slate-200 text-sm text-slate-400 italic"
        data-testid="rec-list"
      >
        No recommendations emitted (exit condition triggered).
      </div>
    );
  }

  // Count unique guidelines.
  const guidelineCount = new Set(cards.map((c) => c.guideline_id)).size;
  const hasConvergence = cards.some((c) => c.convergence.length > 0);

  return (
    <div
      className="px-4 py-3 bg-white border-t border-slate-200 space-y-2 max-h-[40vh] overflow-y-auto"
      data-testid="rec-list"
    >
      <div className="flex items-center gap-3">
        <h3 className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">
          Recommendations
        </h3>
        {guidelineCount > 1 && (
          <span className="text-[10px] text-slate-400">
            {cards.length} recs from {guidelineCount} guidelines
          </span>
        )}
        {hasConvergence && (
          <span className="text-[10px] text-amber-600 font-medium">
            Convergence detected
          </span>
        )}
      </div>
      {cards.map((card) => (
        <RecCard
          key={card.recommendation_id}
          card={card}
          isHighlighted={highlightedRecIds.has(card.recommendation_id)}
          onConvergenceClick={handleConvergenceClick}
        />
      ))}
    </div>
  );
}
