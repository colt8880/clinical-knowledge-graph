"use client";

import type { Recommendation } from "@/lib/eval/trace-nav";

const STATUS_STYLE: Record<string, { border: string; bg: string; text: string; badge: string }> = {
  due: {
    border: "border-blue-300",
    bg: "bg-blue-50",
    text: "text-blue-800",
    badge: "bg-blue-600 text-white",
  },
  up_to_date: {
    border: "border-green-300",
    bg: "bg-green-50",
    text: "text-green-800",
    badge: "bg-green-600 text-white",
  },
  not_applicable: {
    border: "border-slate-200",
    bg: "bg-slate-50",
    text: "text-slate-600",
    badge: "bg-slate-400 text-white",
  },
  insufficient_evidence: {
    border: "border-slate-200",
    bg: "bg-slate-50",
    text: "text-slate-600",
    badge: "bg-slate-400 text-white",
  },
};

const GRADE_BADGE: Record<string, string> = {
  B: "bg-green-600 text-white",
  C: "bg-amber-500 text-white",
  I: "bg-slate-400 text-white",
};

interface RecommendationStripProps {
  recommendations: Recommendation[];
}

export default function RecommendationStrip({
  recommendations,
}: RecommendationStripProps) {
  if (recommendations.length === 0) {
    return (
      <div
        className="px-4 py-3 bg-slate-50 border-t border-slate-200 text-sm text-slate-400 italic"
        data-testid="recommendation-strip"
      >
        No recommendations emitted (exit condition triggered).
      </div>
    );
  }

  return (
    <div
      className="px-4 py-3 bg-white border-t border-slate-200 space-y-2"
      data-testid="recommendation-strip"
    >
      <h3 className="text-[10px] uppercase tracking-wide font-semibold text-slate-500">
        Recommendations
      </h3>
      {recommendations.map((rec) => {
        const style = STATUS_STYLE[rec.status] ?? STATUS_STYLE.not_applicable;
        const gradeBg = GRADE_BADGE[rec.evidence_grade] ?? "bg-slate-400 text-white";

        return (
          <div
            key={rec.recommendation_id}
            className={`rounded border ${style.border} ${style.bg} px-4 py-3`}
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span
                className={`inline-block px-2 py-0.5 text-[11px] font-bold rounded ${gradeBg}`}
              >
                Grade {rec.evidence_grade}
              </span>
              <span
                className={`inline-block px-2 py-0.5 text-[11px] font-semibold uppercase rounded ${style.badge}`}
              >
                {rec.status.replace(/_/g, " ")}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                {rec.recommendation_id}
              </span>
            </div>
            <p className={`text-sm leading-relaxed ${style.text}`}>
              {rec.reason}
            </p>
            {rec.offered_strategies && rec.offered_strategies.length > 0 && (
              <div className="mt-1.5 text-xs text-slate-500">
                Offered strategies: {rec.offered_strategies.join(", ")}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
