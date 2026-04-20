"use client";

import Link from "next/link";
import type { GuidelineMeta } from "@/lib/api/client";

const DOMAIN_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  USPSTF: { bg: "bg-blue-50", border: "border-blue-300", text: "text-blue-800" },
  "ACC/AHA": { bg: "bg-purple-50", border: "border-purple-300", text: "text-purple-800" },
  KDIGO: { bg: "bg-emerald-50", border: "border-emerald-300", text: "text-emerald-800" },
};

const DOMAIN_HEADER_COLORS: Record<string, string> = {
  USPSTF: "bg-blue-600",
  "ACC/AHA": "bg-purple-600",
  KDIGO: "bg-emerald-600",
};

interface GuidelineCardProps {
  guideline: GuidelineMeta;
}

export default function GuidelineCard({ guideline }: GuidelineCardProps) {
  const domain = guideline.domain ?? "Unknown";
  const colors = DOMAIN_COLORS[domain] ?? { bg: "bg-slate-50", border: "border-slate-300", text: "text-slate-800" };
  const headerColor = DOMAIN_HEADER_COLORS[domain] ?? "bg-slate-600";

  const modeledCount = guideline.coverage?.modeled?.length ?? 0;
  const deferredItems = guideline.coverage?.deferred ?? [];

  return (
    <Link
      href={`/explore/${guideline.id}`}
      className={`block rounded-lg border ${colors.border} overflow-hidden hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500`}
      data-testid={`guideline-card-${guideline.id}`}
    >
      <div className={`${headerColor} px-4 py-2`}>
        <span className="text-white text-[11px] font-semibold uppercase tracking-wide">
          {domain}
        </span>
      </div>
      <div className={`${colors.bg} p-4`}>
        <h3 className={`text-sm font-semibold ${colors.text} mb-1 line-clamp-2`}>
          {guideline.title}
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          {guideline.version} — {guideline.rec_count} recommendation{guideline.rec_count !== 1 ? "s" : ""}
        </p>

        {guideline.coverage && (
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="font-medium">Modeled:</span>{" "}
              {modeledCount} grade{modeledCount !== 1 ? "s" : ""}
              {guideline.coverage.modeled.length > 0 && (
                <span className="text-slate-400">
                  {" "}({guideline.coverage.modeled.map((m) => m.label).join(", ")})
                </span>
              )}
            </div>
            {deferredItems.length > 0 && (
              <div>
                <span className="font-medium">Deferred:</span>{" "}
                <span className="text-slate-400">{deferredItems.join(", ")}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
