"use client";

import { Suspense, useCallback, useMemo, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSubgraph } from "@/lib/api/client";
import type { ForestNode, GraphEdge } from "@/lib/api/client";
import GraphCanvas from "@/components/GraphCanvas";
import DomainFilter from "@/components/DomainFilter";
import NodeDetail from "@/components/NodeDetail";
import {
  useExploreUrlState,
  domainKeysToApiLabels,
  type DomainKey,
} from "@/lib/explore/urlState";

export default function ExplorePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-slate-400">
          Loading...
        </div>
      }
    >
      <ExploreContent />
    </Suspense>
  );
}

function ExploreContent() {
  const { domains, focus, setDomains, setFocus } = useExploreUrlState();
  const [detailNodeId, setDetailNodeId] = useState<string | null>(null);
  const [detailEdgeId, setDetailEdgeId] = useState<string | null>(null);

  // Fetch the full forest (all domains) once. Filter client-side.
  const forestQuery = useQuery({
    queryKey: ["subgraph"],
    queryFn: () => fetchSubgraph(),
    staleTime: 5 * 60 * 1000,
  });

  const allNodes: ForestNode[] = useMemo(
    () => forestQuery.data?.nodes ?? [],
    [forestQuery.data],
  );
  const allEdges: GraphEdge[] = useMemo(
    () => forestQuery.data?.edges ?? [],
    [forestQuery.data],
  );

  // Convert domain keys to API labels for visibility filtering.
  const visibleApiDomains = useMemo(
    () => domainKeysToApiLabels(domains),
    [domains],
  );

  // Find the focused/detail node.
  const detailNode = useMemo(() => {
    const id = detailNodeId ?? focus;
    if (!id) return null;
    return allNodes.find((n) => n.id === id) ?? null;
  }, [allNodes, detailNodeId, focus]);

  const detailEdge = useMemo(
    () =>
      detailEdgeId ? allEdges.find((e) => e.id === detailEdgeId) ?? null : null,
    [allEdges, detailEdgeId],
  );

  // Sync focus from URL to detail panel on load.
  useEffect(() => {
    if (focus && !detailNodeId) {
      setDetailNodeId(focus);
    }
  }, [focus, detailNodeId]);

  // ── Click handlers ─────────────────────────────────────────────

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setDetailNodeId(nodeId);
      setDetailEdgeId(null);
      setFocus(nodeId);
    },
    [setFocus],
  );

  const handleEdgeClick = useCallback((edgeId: string) => {
    setDetailEdgeId(edgeId);
    setDetailNodeId(null);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setDetailNodeId(null);
    setDetailEdgeId(null);
    setFocus(null);
  }, [setFocus]);

  const handleDomainChange = useCallback(
    (newDomains: DomainKey[]) => {
      setDomains(newDomains);
    },
    [setDomains],
  );

  // Close detail on Escape.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setDetailNodeId(null);
        setDetailEdgeId(null);
        setFocus(null);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setFocus]);

  return (
    <div className="flex h-full" data-testid="explore-page">
      {/* Left: domain filter sidebar */}
      <aside className="w-[200px] bg-slate-50 border-r border-slate-200 shrink-0">
        <DomainFilter
          visibleDomains={domains}
          onChange={handleDomainChange}
        />
      </aside>

      {/* Center: graph canvas */}
      <div
        className="flex-1 min-w-0 relative"
        onClick={(e) => {
          // Only fire for clicks directly on the container (not canvas).
          if (e.target === e.currentTarget) {
            handleBackgroundClick();
          }
        }}
      >
        {forestQuery.isLoading ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            Loading graph...
          </div>
        ) : forestQuery.error ? (
          <div className="flex items-center justify-center h-full text-red-500 text-sm">
            Error: {(forestQuery.error as Error).message}
          </div>
        ) : (
          <GraphCanvas
            nodes={allNodes}
            edges={allEdges}
            visibleDomains={visibleApiDomains}
            focusedNodeId={focus}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            selectedNodeId={detailNodeId}
            selectedEdgeId={detailEdgeId}
          />
        )}
      </div>

      {/* Right: detail panel */}
      <aside className="w-[420px] bg-slate-50 border-l border-slate-200 overflow-y-auto shrink-0">
        <NodeDetail node={detailNode} edge={detailEdge} />
      </aside>
    </div>
  );
}
