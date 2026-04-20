"use client";

import type { GuidelineMeta } from "@/lib/api/client";

interface CoverageViewProps {
  guideline: GuidelineMeta;
}

const GRADE_BADGE_COLORS: Record<string, string> = {
  B: "bg-green-100 text-green-800 border-green-300",
  C: "bg-amber-100 text-amber-800 border-amber-300",
  I: "bg-slate-100 text-slate-600 border-slate-300",
};

function gradeBadge(label: string): string {
  // Extract grade letter from label like "Grade B" or "COR I, LOE A".
  for (const key of Object.keys(GRADE_BADGE_COLORS)) {
    if (label.includes(`Grade ${key}`)) return key;
  }
  return "";
}

export default function CoverageView({ guideline }: CoverageViewProps) {
  const coverage = guideline.coverage;

  if (!coverage) {
    return (
      <div className="p-6 text-slate-400 italic" role="tabpanel" id="panel-coverage">
        No coverage data available for this guideline.
      </div>
    );
  }

  return (
    <div
      className="p-6 max-w-3xl"
      role="tabpanel"
      id="panel-coverage"
      data-testid="coverage-view"
    >
      <h2 className="text-base font-semibold text-slate-900 mb-4">
        Coverage Summary
      </h2>

      {/* Modeled Recommendations */}
      <section className="mb-6">
        <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
          Modeled Recommendations ({coverage.modeled.length})
        </h3>
        {coverage.modeled.length > 0 ? (
          <table className="w-full text-sm" data-testid="modeled-table">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-4 text-slate-500 font-medium">Label</th>
                <th className="text-left py-2 text-slate-500 font-medium">Rec ID</th>
              </tr>
            </thead>
            <tbody>
              {coverage.modeled.map((m, i) => {
                const grade = gradeBadge(m.label);
                const badgeClass = grade
                  ? GRADE_BADGE_COLORS[grade]
                  : "bg-slate-100 text-slate-600 border-slate-300";
                return (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2 pr-4">
                      {grade && (
                        <span
                          className={`inline-block px-1.5 py-0.5 text-[10px] font-semibold rounded border mr-2 ${badgeClass}`}
                        >
                          {grade}
                        </span>
                      )}
                      {m.label}
                    </td>
                    <td className="py-2 font-mono text-xs text-slate-500">
                      {m.rec_id}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-slate-400 italic">None</p>
        )}
      </section>

      {/* Deferred Areas */}
      {coverage.deferred.length > 0 && (
        <section className="mb-6">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Deferred Areas
          </h3>
          <ul className="list-disc list-inside text-sm text-slate-600 space-y-1" data-testid="deferred-list">
            {coverage.deferred.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Exit-Only Areas */}
      {coverage.exit_only.length > 0 && (
        <section className="mb-6">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Exit-Only (not modeled, triggers exit event)
          </h3>
          <ul className="list-disc list-inside text-sm text-slate-600 space-y-1" data-testid="exit-only-list">
            {coverage.exit_only.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
