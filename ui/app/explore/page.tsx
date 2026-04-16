"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useQueries } from "@tanstack/react-query";
import { fetchNeighbors } from "@/lib/api/client";
import type { GraphNode, GraphEdge } from "@/lib/api/client";
import GraphCanvas from "@/components/GraphCanvas";
import NodeDetail from "@/components/NodeDetail";

/**
 * Default entry point: the statin guideline node.
 * Users land here and expand outward.
 */
const DEFAULT_PINNED = "guideline:uspstf-statin-2022";

/**
 * Parse the URL state.
 *  - pinned: the center node whose neighbors are rendered.
 *  - expanded: comma-separated list of node IDs whose neighbors
 *    have also been fetched (multi-hop exploration).
 */
function useUrlState() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const pinned = searchParams.get("pinned") ?? DEFAULT_PINNED;
  const expanded = useMemo(() => {
    const raw = searchParams.get("expanded");
    if (!raw) return [] as string[];
    return raw.split(",").filter(Boolean);
  }, [searchParams]);

  const setUrlState = useCallback(
    (nextPinned: string, nextExpanded: string[]) => {
      const params = new URLSearchParams();
      params.set("pinned", nextPinned);
      if (nextExpanded.length > 0) {
        params.set("expanded", nextExpanded.join(","));
      }
      router.push(`/explore?${params.toString()}`);
    },
    [router],
  );

  return { pinned, expanded, setUrlState };
}

/**
 * Merge multiple Subgraph responses into a single nodes + edges
 * collection for the canvas. Deduplicates by id.
 */
function useMergedGraph(
  pinnedId: string,
  expandedIds: string[],
) {
  // Fetch the pinned node's neighborhood.
  const pinnedQuery = useQuery({
    queryKey: ["neighbors", pinnedId],
    queryFn: () => fetchNeighbors(pinnedId),
  });

  // Fetch each expanded node's neighborhood.
  const expandedResults = useQueries({
    queries: expandedIds.map((id) => ({
      queryKey: ["neighbors", id],
      queryFn: () => fetchNeighbors(id),
      enabled: !!id,
    })),
  });

  const isLoading =
    pinnedQuery.isLoading || expandedResults.some((q) => q.isLoading);
  const error = pinnedQuery.error ?? expandedResults.find((q) => q.error)?.error;

  // Merge all subgraphs.
  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();
    const edgeMap = new Map<string, GraphEdge>();

    function ingest(subgraph: { nodes: GraphNode[]; edges: GraphEdge[] } | undefined) {
      if (!subgraph) return;
      for (const n of subgraph.nodes) {
        if (!nodeMap.has(n.id)) nodeMap.set(n.id, n);
      }
      for (const e of subgraph.edges) {
        if (!edgeMap.has(e.id)) edgeMap.set(e.id, e);
      }
    }

    ingest(pinnedQuery.data);
    for (const eq of expandedResults) {
      ingest(eq.data);
    }

    return {
      nodes: Array.from(nodeMap.values()),
      edges: Array.from(edgeMap.values()),
    };
  }, [pinnedQuery.data, expandedResults]);

  return { nodes, edges, isLoading, error };
}

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
  const { pinned, expanded, setUrlState } = useUrlState();
  const { nodes, edges, isLoading, error } = useMergedGraph(pinned, expanded);

  // Detail panel state: either a node or an edge.
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );

  const selectedEdge = useMemo(
    () => edges.find((e) => e.id === selectedEdgeId) ?? null,
    [edges, selectedEdgeId],
  );

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      setSelectedEdgeId(null);

      // If this node isn't already expanded and isn't the pinned node,
      // expand it (fetch its neighbors and add to the graph).
      if (nodeId !== pinned && !expanded.includes(nodeId)) {
        setUrlState(pinned, [...expanded, nodeId]);
      }
    },
    [pinned, expanded, setUrlState],
  );

  const handleEdgeClick = useCallback(
    (edgeId: string) => {
      setSelectedEdgeId(edgeId);
      setSelectedNodeId(null);
    },
    [],
  );

  // Navigate to a new center node (double-click behavior or explicit nav).
  const handleNavigate = useCallback(
    (nodeId: string) => {
      setUrlState(nodeId, []);
      setSelectedNodeId(nodeId);
      setSelectedEdgeId(null);
    },
    [setUrlState],
  );

  return (
    <div className="flex h-full" data-testid="explore-page">
      {/* Left: node list for quick navigation */}
      <aside className="w-56 bg-slate-50 border-r border-slate-200 overflow-y-auto shrink-0">
        <div className="p-3">
          <h2 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Nodes ({nodes.length})
          </h2>
          {isLoading && (
            <p className="text-xs text-slate-400">Loading...</p>
          )}
          {error && (
            <p className="text-xs text-red-500">
              Error: {(error as Error).message}
            </p>
          )}
          <ul className="space-y-0.5">
            {nodes.map((n) => {
              const label =
                (n.properties.title as string) ??
                (n.properties.name as string) ??
                (n.properties.display_name as string) ??
                n.id;
              const isActive = n.id === selectedNodeId;
              return (
                <li key={n.id}>
                  <button
                    onClick={() => handleNavigate(n.id)}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs truncate transition-colors ${
                      isActive
                        ? "bg-blue-100 text-blue-800 font-medium"
                        : "text-slate-700 hover:bg-slate-100"
                    }`}
                    title={`${n.id} — click to navigate`}
                  >
                    <span className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
                      style={{
                        backgroundColor:
                          n.labels[0] === "Guideline" ? "#6b21a8" :
                          n.labels[0] === "Recommendation" ? "#1e40af" :
                          n.labels[0] === "Strategy" ? "#92400e" :
                          n.labels[0] === "Condition" ? "#991b1b" :
                          n.labels[0] === "Procedure" ? "#166534" :
                          n.labels[0] === "Observation" ? "#3730a3" :
                          n.labels[0] === "Medication" ? "#9d174d" :
                          "#64748b",
                      }}
                    />
                    {label}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </aside>

      {/* Center: graph canvas */}
      <div className="flex-1 min-w-0 relative">
        {nodes.length > 0 && (
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            selectedNodeId={selectedNodeId}
          />
        )}
        {isLoading && nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400">
            Loading graph...
          </div>
        )}
      </div>

      {/* Right: detail panel */}
      <aside className="w-[420px] bg-slate-50 border-l border-slate-200 overflow-y-auto shrink-0">
        <NodeDetail node={selectedNode} edge={selectedEdge} />
      </aside>
    </div>
  );
}
