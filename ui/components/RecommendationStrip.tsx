"use client";

import type { Recommendation } from "@/lib/eval/trace-nav";

const STATUS_BADGE: Record<string, { bg: string; text: string }> = {
  due: { bg: "bg-blue-100 border-blue-300", text: "text-blue-800" },
  up_to_date: { bg: "bg-green-100 border-green-300", text: "text-green-800" },
  not_applicable: { bg: "bg-slate-100 border-slate-300", text: "text-slate-600" },
  insufficient_evidence: { bg: "bg-slate-100 border-slate-300", text: "text-slate-600" },
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
  if (recommendations.length === 0) return null;

  return (
    <div
      className="flex gap-3 px-4 py-3 bg-slate-50 border-t border-slate-200 overflow-x-auto"
      data-testid="recommendation-strip"
    >
      {recommendations.map((rec) => {
        const status = STATUS_BADGE[rec.status] ?? STATUS_BADGE.not_applicable;
        const gradeBg = GRADE_BADGE[rec.evidence_grade] ?? "bg-slate-400 text-white";

        return (
          <div
            key={rec.recommendation_id}
            className={`flex items-center gap-2 px-3 py-2 rounded border text-sm shrink-0 ${status.bg}`}
          >
            <span
              className={`inline-block px-1.5 py-0.5 text-[10px] font-bold rounded ${gradeBg}`}
            >
              {rec.evidence_grade}
            </span>
            <span className={`font-medium ${status.text}`}>{rec.status}</span>
            <span className="text-xs text-slate-500 max-w-[300px] truncate">
              {rec.reason}
            </span>
          </div>
        );
      })}
    </div>
  );
}
