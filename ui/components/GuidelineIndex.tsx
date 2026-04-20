"use client";

import Link from "next/link";
import type { GuidelineMeta } from "@/lib/api/client";
import GuidelineCard from "./GuidelineCard";

interface GuidelineIndexProps {
  guidelines: GuidelineMeta[];
}

export default function GuidelineIndex({ guidelines }: GuidelineIndexProps) {
  return (
    <div className="max-w-5xl mx-auto p-8" data-testid="guideline-index">
      <h1 className="text-xl font-semibold text-slate-900 mb-1">
        Clinical Guidelines
      </h1>
      <p className="text-sm text-slate-500 mb-6">
        Select a guideline to inspect its encoded logic, coverage, and provenance.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {guidelines.map((g) => (
          <GuidelineCard key={g.id} guideline={g} />
        ))}

        {/* "All guidelines" card linking to whole-forest view */}
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
  );
}
