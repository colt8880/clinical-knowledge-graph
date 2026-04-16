"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchNeighbors } from "@/lib/api/client";
import type { GraphNode, Subgraph } from "@/lib/api/client";
import GraphCanvas from "@/components/GraphCanvas";
import NodeDetail from "@/components/NodeDetail";

/**
 * Default entry point: the statin guideline node.
 * Users land here and expand outward.
 */
const DEFAULT_PINNED = "guideline:uspstf-statin-2022";

/**
 * URL state is now just `?pinned=<id>`.
 * The graph shows the pinned node + its direct children only.
 * Clicking a child navigates down (makes it the new pinned node).
 * Clicking the parent navigates back up.
 */
function useUrlState() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const pinned = searchParams.get("pinned") ?? DEFAULT_PINNED;

  const navigate = useCallback(
    (nextPinned: string) => {
      const params = new URLSearchParams();
      params.set("pinned", nextPinned);
      router.push(`/explore?${params.toString()}`);
    },
    [router],
  );

  return { pinned, navigate };
}

/**
 * Given a Subgraph response, identify the parent node of the center.
 * The parent is a node connected by an edge where the center is the
 * edge's start (outgoing from center, e.g. FROM_GUIDELINE points
 * Rec -> Guideline, OFFERS_STRATEGY points Rec -> Strategy is actually
 * wrong direction). We use the graph structure: a parent is a neighbor
 * that, if you navigated to it, the current center would appear as its child.
 *
 * Heuristic: the parent is the node with the "higher" type in the hierarchy:
 * Guideline > Recommendation > Strategy > (Medication/Procedure/Observation)
 */
const TYPE_RANK: Record<string, number> = {
  Guideline: 0,
  Recommendation: 1,
  Strategy: 2,
  Condition: 3,
  Medication: 4,
  Procedure: 4,
  Observation: 4,
};

function findParentId(
  subgraph: Subgraph,
): string | null {
  const centerNode = subgraph.nodes.find((n) => n.id === subgraph.center);
  if (!centerNode) return null;
  const centerRank = TYPE_RANK[centerNode.labels[0]] ?? 99;

  // Find neighbors with a lower (higher in hierarchy) rank.
  let bestParent: GraphNode | null = null;
  let bestRank = centerRank;
  for (const node of subgraph.nodes) {
    if (node.id === subgraph.center) continue;
    const rank = TYPE_RANK[node.labels[0]] ?? 99;
    if (rank < bestRank) {
      bestRank = rank;
      bestParent = node;
    }
  }
  return bestParent?.id ?? null;
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
  const { pinned, navigate } = useUrlState();

  // Fetch only the pinned node's direct neighbors.
  const { data: subgraph, isLoading, error } = useQuery({
    queryKey: ["neighbors", pinned],
    queryFn: () => fetchNeighbors(pinned),
  });

  // Detail panel state.
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // Filter: only show the center node + its children (nodes at the same
  // or lower level in the hierarchy). Siblings at the same level as center
  // that come from the parent are excluded — only children are shown.
  const { visibleNodes, visibleEdges, parentId } = useMemo(() => {
    if (!subgraph) return { visibleNodes: [], visibleEdges: [], parentId: null };

    const parentId = findParentId(subgraph);
    const centerNode = subgraph.nodes.find((n) => n.id === subgraph.center);
    if (!centerNode) return { visibleNodes: [], visibleEdges: [], parentId: null };

    const centerRank = TYPE_RANK[centerNode.labels[0]] ?? 99;

    // Keep: the center node, plus neighbors that are children (higher rank number)
    // or the parent (for back-navigation). Exclude siblings at the same rank.
    const visibleNodes = subgraph.nodes.filter((n) => {
      if (n.id === subgraph.center) return true;
      if (n.id === parentId) return true;
      const rank = TYPE_RANK[n.labels[0]] ?? 99;
      return rank > centerRank;
    });

    const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));

    // Only keep edges between visible nodes.
    const visibleEdges = subgraph.edges.filter(
      (e) => visibleNodeIds.has(e.start) && visibleNodeIds.has(e.end),
    );

    return { visibleNodes, visibleEdges, parentId };
  }, [subgraph]);

  const selectedNode = useMemo(
    () => visibleNodes.find((n) => n.id === selectedNodeId) ?? null,
    [visibleNodes, selectedNodeId],
  );

  const selectedEdge = useMemo(
    () => visibleEdges.find((e) => e.id === selectedEdgeId) ?? null,
    [visibleEdges, selectedEdgeId],
  );

  // Clicking a node: navigate to it (hierarchical traversal).
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      setSelectedEdgeId(null);

      // If clicking the center node, just select it (show detail).
      if (nodeId === pinned) return;

      // Navigate to the clicked node (down to a child, or up to parent).
      navigate(nodeId);
    },
    [pinned, navigate],
  );

  const handleEdgeClick = useCallback(
    (edgeId: string) => {
      setSelectedEdgeId(edgeId);
      setSelectedNodeId(null);
    },
    [],
  );

  const centerNode = useMemo(
    () => visibleNodes.find((n) => n.id === pinned) ?? null,
    [visibleNodes, pinned],
  );

  const centerLabel = centerNode
    ? ((centerNode.properties.title as string) ??
       (centerNode.properties.name as string) ??
       (centerNode.properties.display_name as string) ??
       centerNode.id)
    : pinned;

  return (
    <div className="flex h-full" data-testid="explore-page">
      {/* Left: node list with hierarchy context */}
      <aside className="w-60 bg-slate-50 border-r border-slate-200 overflow-y-auto shrink-0">
        <div className="p-3">
          {/* Back to parent button */}
          {parentId && (
            <button
              onClick={() => navigate(parentId)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 mb-3 px-1 py-1 rounded hover:bg-slate-100 transition-colors w-full"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to parent
            </button>
          )}

          <h2 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-1">
            Current
          </h2>
          <div className="text-sm font-medium text-slate-900 mb-3 px-1">
            {centerLabel}
          </div>

          <h2 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Children ({visibleNodes.filter((n) => n.id !== pinned && n.id !== parentId).length})
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
            {visibleNodes
              .filter((n) => n.id !== pinned && n.id !== parentId)
              .map((n) => {
                const label =
                  (n.properties.title as string) ??
                  (n.properties.name as string) ??
                  (n.properties.display_name as string) ??
                  n.id;
                const isActive = n.id === selectedNodeId;
                return (
                  <li key={n.id}>
                    <button
                      onClick={() => handleNodeClick(n.id)}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                        isActive
                          ? "bg-blue-100 text-blue-800 font-medium"
                          : "text-slate-700 hover:bg-slate-100"
                      }`}
                      title={`${n.id} — click to navigate`}
                    >
                      <span
                        className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
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
        {visibleNodes.length > 0 && (
          <GraphCanvas
            nodes={visibleNodes}
            edges={visibleEdges}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            selectedNodeId={selectedNodeId}
          />
        )}
        {isLoading && visibleNodes.length === 0 && (
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
