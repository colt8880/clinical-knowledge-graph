"use client";

import { Suspense, useMemo, useCallback } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchSubgraph, fetchGuidelines } from "@/lib/api/client";
import { extractScopedSubgraph } from "@/lib/explore/scopedSubgraph";
import GuidelineDetailTabs, { type TabKey } from "@/components/GuidelineDetailTabs";
import LogicView from "@/components/LogicView";
import CoverageView from "@/components/CoverageView";
import ProvenanceView from "@/components/ProvenanceView";

export default function GuidelineDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-slate-400">
          Loading...
        </div>
      }
    >
      <GuidelineDetailContent />
    </Suspense>
  );
}

function GuidelineDetailContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const guidelineSlug = params.guideline as string;

  const activeTab = (searchParams.get("tab") as TabKey) || "logic";
  const focusNodeId = searchParams.get("focus") ?? null;

  // Fetch the full forest (cached).
  const forestQuery = useQuery({
    queryKey: ["subgraph"],
    queryFn: () => fetchSubgraph(),
    staleTime: 5 * 60 * 1000,
  });

  // Fetch guideline metadata for coverage and provenance tabs.
  const guidelinesQuery = useQuery({
    queryKey: ["guidelines"],
    queryFn: fetchGuidelines,
    staleTime: 5 * 60 * 1000,
  });

  // Extract scoped subgraph.
  const scoped = useMemo(() => {
    if (!forestQuery.data) return null;
    return extractScopedSubgraph(forestQuery.data, guidelineSlug);
  }, [forestQuery.data, guidelineSlug]);

  // Find guideline metadata for this slug.
  const guidelineMeta = useMemo(() => {
    if (!guidelinesQuery.data) return null;
    return guidelinesQuery.data.find((g) => g.id === guidelineSlug) ?? null;
  }, [guidelinesQuery.data, guidelineSlug]);

  const handleFocusChange = useCallback(
    (nodeId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nodeId) {
        params.set("focus", nodeId);
      } else {
        params.delete("focus");
      }
      const qs = params.toString();
      router.push(`/explore/${guidelineSlug}${qs ? `?${qs}` : ""}`);
    },
    [router, searchParams, guidelineSlug],
  );

  const isLoading = forestQuery.isLoading || guidelinesQuery.isLoading;
  const error = forestQuery.error || guidelinesQuery.error;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        Loading guideline...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500 text-sm">
        Error: {(error as Error).message}
      </div>
    );
  }

  if (!scoped || scoped.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
        <p>Guideline not found: {guidelineSlug}</p>
        <Link href="/explore" className="text-blue-600 hover:underline text-sm">
          Back to index
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" data-testid="guideline-detail-page">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-3 shrink-0">
        <div className="flex items-center gap-3 mb-1">
          <Link
            href="/explore"
            className="text-slate-400 hover:text-slate-600 text-sm"
          >
            Guidelines
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-medium text-slate-700">
            {guidelineMeta?.title ?? guidelineSlug}
          </span>
        </div>
        <GuidelineDetailTabs
          activeTab={activeTab}
          guidelineSlug={guidelineSlug}
        />
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === "logic" && (
          <LogicView
            scoped={scoped}
            focusNodeId={focusNodeId}
            onFocusChange={handleFocusChange}
          />
        )}
        {activeTab === "coverage" && guidelineMeta && (
          <div className="overflow-y-auto h-full">
            <CoverageView guideline={guidelineMeta} />
          </div>
        )}
        {activeTab === "provenance" && guidelineMeta && (
          <div className="overflow-y-auto h-full">
            <ProvenanceView guideline={guidelineMeta} />
          </div>
        )}
      </div>
    </div>
  );
}
