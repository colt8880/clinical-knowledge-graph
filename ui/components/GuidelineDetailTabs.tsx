"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

export type TabKey = "logic" | "coverage" | "provenance";

const TABS: { key: TabKey; label: string }[] = [
  { key: "logic", label: "Logic" },
  { key: "coverage", label: "Coverage" },
  { key: "provenance", label: "Provenance" },
];

interface GuidelineDetailTabsProps {
  activeTab: TabKey;
  guidelineSlug: string;
}

export default function GuidelineDetailTabs({
  activeTab,
  guidelineSlug,
}: GuidelineDetailTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleTabChange = useCallback(
    (tab: TabKey) => {
      const params = new URLSearchParams(searchParams.toString());
      if (tab === "logic") {
        params.delete("tab");
      } else {
        params.set("tab", tab);
      }
      const qs = params.toString();
      router.push(`/explore/${guidelineSlug}${qs ? `?${qs}` : ""}`);
    },
    [router, searchParams, guidelineSlug],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const currentIndex = TABS.findIndex((t) => t.key === activeTab);
      if (e.key === "ArrowRight") {
        e.preventDefault();
        const next = TABS[(currentIndex + 1) % TABS.length];
        handleTabChange(next.key);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prev = TABS[(currentIndex - 1 + TABS.length) % TABS.length];
        handleTabChange(prev.key);
      }
    },
    [activeTab, handleTabChange],
  );

  return (
    <div
      className="flex border-b border-slate-200"
      role="tablist"
      aria-label="Guideline detail tabs"
    >
      {TABS.map((tab) => {
        const isActive = tab.key === activeTab;
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${tab.key}`}
            tabIndex={isActive ? 0 : -1}
            className={`px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset ${
              isActive
                ? "text-blue-700 border-b-2 border-blue-700 -mb-px"
                : "text-slate-500 hover:text-slate-700"
            }`}
            onClick={() => handleTabChange(tab.key)}
            onKeyDown={handleKeyDown}
            data-testid={`tab-${tab.key}`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
