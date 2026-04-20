"use client";

import Link from "next/link";
import type { GuidelineMeta } from "@/lib/api/client";
import GuidelineCard from "./GuidelineCard";

interface GuidelineIndexProps {
  guidelines: GuidelineMeta[];
}

/** Map guideline IDs to clinical categories for grouping. */
const CATEGORY_MAP: Record<string, string> = {
  "uspstf-statin-2022": "Cardiovascular",
  "acc-aha-cholesterol-2018": "Cardiovascular",
  "kdigo-ckd-2024": "Renal",
};

/** Stable ordering for categories. */
const CATEGORY_ORDER = ["Cardiovascular", "Renal"];

function groupByCategory(
  guidelines: GuidelineMeta[],
): { category: string; items: GuidelineMeta[] }[] {
  const groups = new Map<string, GuidelineMeta[]>();

  for (const g of guidelines) {
    const cat = CATEGORY_MAP[g.id] ?? "Other";
    const list = groups.get(cat) ?? [];
    list.push(g);
    groups.set(cat, list);
  }

  // Sort categories in stable order; unknown categories go last.
  const result: { category: string; items: GuidelineMeta[] }[] = [];
  for (const cat of CATEGORY_ORDER) {
    const items = groups.get(cat);
    if (items) {
      result.push({ category: cat, items });
      groups.delete(cat);
    }
  }
  // Any remaining categories not in CATEGORY_ORDER.
  groups.forEach((items, cat) => {
    result.push({ category: cat, items });
  });
  return result;
}

export default function GuidelineIndex({ guidelines }: GuidelineIndexProps) {
  const grouped = groupByCategory(guidelines);

  return (
    <div className="max-w-5xl mx-auto p-8" data-testid="guideline-index">
      <h1 className="text-xl font-semibold text-slate-900 mb-1">
        Clinical Guidelines
      </h1>
      <p className="text-sm text-slate-500 mb-6">
        Select a guideline to inspect its encoded logic, coverage, and provenance.
      </p>

      {grouped.map(({ category, items }) => (
        <div key={category} className="mb-8">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400 mb-3">
            {category}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((g) => (
              <GuidelineCard key={g.id} guideline={g} />
            ))}
          </div>
        </div>
      ))}

      {/* "All guidelines" card at the bottom */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400 mb-3">
          Cross-guideline
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Link
            href="/explore/all"
            className="block rounded-lg border border-slate-300 overflow-hidden hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="guideline-card-all"
          >
            <div className="bg-slate-600 px-4 py-2">
              <span className="text-white text-[11px] font-semibold uppercase tracking-wide">
                All Guidelines
              </span>
            </div>
            <div className="bg-slate-50 p-4">
              <h3 className="text-sm font-semibold text-slate-800 mb-1">
                Whole-forest view
              </h3>
              <p className="text-xs text-slate-500">
                View all guidelines on a single canvas with domain filtering.
                Shows cross-guideline edges and shared clinical entities.
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
