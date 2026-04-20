"use client";

import { Suspense, useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { fetchInteractions, type InteractionsResponse } from "@/lib/api/client";
import type { EdgeTypeFilter } from "@/lib/interactions/collapse";
import InteractionsCanvas from "@/components/InteractionsCanvas";
import InteractionsLegend from "@/components/InteractionsLegend";
import InteractionDetail from "@/components/InteractionDetail";

function parseEdgeType(val: string | null): EdgeTypeFilter {
  if (val === "preemption" || val === "modifier" || val === "both") return val;
  return "both";
}

function parseGuidelines(val: string | null): Set<string> {
  if (!val) return new Set();
  const VALID = new Set(["USPSTF", "ACC/AHA", "KDIGO"]);
  const slugToDisplay: Record<string, string> = {
    uspstf: "USPSTF",
    "acc-aha": "ACC/AHA",
    kdigo: "KDIGO",
  };
  const result = new Set<string>();
  for (const s of val.split(",")) {
    const mapped = slugToDisplay[s.trim().toLowerCase()];
    if (mapped && VALID.has(mapped)) result.add(mapped);
  }
  return result;
}

export default function InteractionsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-slate-400">
          Loading...
        </div>
      }
    >
      <InteractionsContent />
    </Suspense>
  );
}

function InteractionsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [data, setData] = useState<InteractionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Local state — initialised from URL, then owned by React.
  const [edgeTypeFilter, setEdgeTypeFilter] = useState<EdgeTypeFilter>(
    parseEdgeType(searchParams.get("type")),
  );
  const [focusId, setFocusId] = useState<string | null>(searchParams.get("focus"));
  const [selectedGuidelines, setSelectedGuidelines] = useState<Set<string>>(
    parseGuidelines(searchParams.get("guidelines")),
  );

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(focusId);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  const hasSelection = selectedGuidelines.size >= 2;

  // Sync local state changes back to URL.
  const syncUrl = useCallback(
    (params: Record<string, string | null>) => {
      const sp = new URLSearchParams(searchParams.toString());
      for (const [key, val] of Object.entries(params)) {
        if (val === null || val === "") {
          sp.delete(key);
        } else {
          sp.set(key, val);
        }
      }
      const qs = sp.toString();
      router.replace(`/interactions${qs ? `?${qs}` : ""}`, { scroll: false });
    },
    [searchParams, router],
  );

  // Fetch all data on mount (we filter client-side by selected guidelines).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchInteractions("both")
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, []);

  // Guideline slug mapping for URL sync.
  const domainToSlug: Record<string, string> = {
    USPSTF: "uspstf",
    "ACC/AHA": "acc-aha",
    KDIGO: "kdigo",
  };

  const handleToggleGuideline = useCallback(
    (domain: string) => {
      setSelectedGuidelines((prev) => {
        const next = new Set(prev);
        if (next.has(domain)) {
          next.delete(domain);
        } else {
          next.add(domain);
        }
        const slugs = Array.from(next).map((d) => domainToSlug[d] ?? d.toLowerCase()).join(",");
        syncUrl({ guidelines: slugs || null });
        return next;
      });
    },
    [syncUrl, domainToSlug],
  );

  const handleEdgeTypeChange = useCallback(
    (filter: EdgeTypeFilter) => {
      setEdgeTypeFilter(filter);
      syncUrl({ type: filter === "both" ? null : filter });
    },
    [syncUrl],
  );

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setSelectedEdgeId(null);
      setSelectedNodeId(nodeId);
      setFocusId(nodeId);
      syncUrl({ focus: nodeId });
    },
    [syncUrl],
  );

  const handleEdgeClick = useCallback(
    (edgeId: string) => {
      setSelectedNodeId(null);
      setSelectedEdgeId(edgeId);
      syncUrl({ focus: edgeId });
    },
    [syncUrl],
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setFocusId(null);
    syncUrl({ focus: null });
  }, [syncUrl]);

  // Filter data to only include edges between selected guidelines.
  const filteredData = useMemo(() => {
    if (!data || !hasSelection) return null;
    return {
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
    };
  }, [data, selectedGuidelines, hasSelection]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-slate-500">
        Loading interactions...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-red-600">
        Error: {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex h-full" data-testid="interactions-page">
      <InteractionsLegend
        data={data}
        edgeTypeFilter={edgeTypeFilter}
        onEdgeTypeChange={handleEdgeTypeChange}
        selectedGuidelines={selectedGuidelines}
        onToggleGuideline={handleToggleGuideline}
      />
      <div className="flex-1 relative">
        {hasSelection && filteredData ? (
          <InteractionsCanvas
            data={filteredData}
            edgeTypeFilter={edgeTypeFilter}
            focusNodeId={focusId}
            selectedNodeId={selectedNodeId}
            selectedEdgeId={selectedEdgeId}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            onBackgroundClick={handleBackgroundClick}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-sm">
              <p className="text-sm text-slate-500 mb-1">
                Select two or more guidelines to compare
              </p>
              <p className="text-xs text-slate-400">
                Choose from the sidebar to view preemption and modifier edges between guidelines.
              </p>
            </div>
          </div>
        )}
      </div>
      {hasSelection && filteredData ? (
        <InteractionDetail
          data={filteredData}
          selectedEdgeId={selectedEdgeId}
          selectedNodeId={selectedNodeId}
        />
      ) : (
        <div className="w-72 border-l border-slate-200 bg-white" />
      )}
    </div>
  );
}
