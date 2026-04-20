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

  // URL-synced state.
  const edgeTypeFilter = parseEdgeType(searchParams.get("type"));
  const focusNodeId = searchParams.get("focus");
  const guidelinesParam = searchParams.get("guidelines");

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(focusNodeId);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [excludedPairs, setExcludedPairs] = useState<Set<string>>(new Set());

  // Build visible guidelines set from excluded pairs.
  const visibleGuidelines = useMemo(() => {
    if (excludedPairs.size === 0) return undefined; // All visible.
    // We don't actually hide full guidelines via pair filter — we filter edges
    // at the collapse level using the pair filter indirectly. For now, pass undefined
    // (all visible) and let the collapse function handle edge filtering.
    return undefined;
  }, [excludedPairs]);

  // Fetch data on mount.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const guidelinesList = guidelinesParam
      ? guidelinesParam.split(",").map((s) => s.trim()).filter(Boolean)
      : undefined;

    fetchInteractions("both", guidelinesList)
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
  }, [guidelinesParam]);

  // Sync URL state.
  const updateUrl = useCallback(
    (params: Record<string, string | null>) => {
      const sp = new URLSearchParams(searchParams.toString());
      for (const [key, val] of Object.entries(params)) {
        if (val === null || val === "" || val === "both") {
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

  const handleEdgeTypeChange = useCallback(
    (filter: EdgeTypeFilter) => {
      updateUrl({ type: filter === "both" ? null : filter });
    },
    [updateUrl],
  );

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setSelectedEdgeId(null);
      setSelectedNodeId(nodeId);
      updateUrl({ focus: nodeId });
    },
    [updateUrl],
  );

  const handleEdgeClick = useCallback(
    (edgeId: string) => {
      setSelectedNodeId(null);
      setSelectedEdgeId(edgeId);
      updateUrl({ focus: edgeId });
    },
    [updateUrl],
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    updateUrl({ focus: null });
  }, [updateUrl]);

  const handleTogglePair = useCallback((pairKey: string) => {
    setExcludedPairs((prev) => {
      const next = new Set(prev);
      if (next.has(pairKey)) {
        next.delete(pairKey);
      } else {
        next.add(pairKey);
      }
      return next;
    });
  }, []);

  // Filter data edges based on excluded pairs before passing to canvas.
  const filteredData = useMemo(() => {
    if (!data || excludedPairs.size === 0) return data;
    return {
      ...data,
      edges: data.edges.filter((edge) => {
        const sourceRec = data.recommendations.find((r) => r.id === edge.source);
        const targetRec = data.recommendations.find((r) => r.id === edge.target);
        if (!sourceRec?.domain || !targetRec?.domain) return true;
        const key = [sourceRec.domain, targetRec.domain].sort().join(":");
        return !excludedPairs.has(key);
      }),
    };
  }, [data, excludedPairs]);

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

  if (!data || !filteredData) return null;

  return (
    <div className="flex h-full" data-testid="interactions-page">
      <InteractionsLegend
        data={data}
        edgeTypeFilter={edgeTypeFilter}
        onEdgeTypeChange={handleEdgeTypeChange}
        excludedPairs={excludedPairs}
        onTogglePair={handleTogglePair}
      />
      <div className="flex-1 relative">
        <InteractionsCanvas
          data={filteredData}
          edgeTypeFilter={edgeTypeFilter}
          visibleGuidelines={visibleGuidelines}
          focusNodeId={focusNodeId}
          selectedNodeId={selectedNodeId}
          selectedEdgeId={selectedEdgeId}
          onNodeClick={handleNodeClick}
          onEdgeClick={handleEdgeClick}
          onBackgroundClick={handleBackgroundClick}
        />
      </div>
      <InteractionDetail
        data={data}
        selectedEdgeId={selectedEdgeId}
        selectedNodeId={selectedNodeId}
      />
    </div>
  );
}
