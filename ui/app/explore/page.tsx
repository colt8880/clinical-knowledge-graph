"use client";

import { Suspense, useCallback, useMemo, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchNeighbors } from "@/lib/api/client";
import type { GraphNode, GraphEdge } from "@/lib/api/client";
import GraphCanvas, { type CanvasColumn } from "@/components/GraphCanvas";
import { filterChildren } from "@/components/ColumnBrowser";
import NodeDetail from "@/components/NodeDetail";

const DEFAULT_GUIDELINE = "guideline:uspstf-statin-2022";

/** Hierarchy rank — used to determine which column a clicked node belongs to. */
const TYPE_RANK: Record<string, number> = {
  Guideline: 0,
  Recommendation: 1,
  Strategy: 2,
  Condition: 3,
  Medication: 3,
  Procedure: 3,
  Observation: 3,
};

/**
 * URL state: ?g=<guideline>&r=<rec>&s=<strategy>
 * Each param records which node is selected at that level.
 */
function useUrlState() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const guideline = searchParams.get("g") ?? DEFAULT_GUIDELINE;
  const rec = searchParams.get("r") ?? null;
  const strategy = searchParams.get("s") ?? null;

  const setSelection = useCallback(
    (g: string, r: string | null, s: string | null) => {
      const params = new URLSearchParams();
      params.set("g", g);
      if (r) params.set("r", r);
      if (s) params.set("s", s);
      router.push(`/explore?${params.toString()}`);
    },
    [router],
  );

  return { guideline, rec, strategy, setSelection };
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
  const { guideline, rec, strategy, setSelection } = useUrlState();
  const [detailNodeId, setDetailNodeId] = useState<string | null>(null);
  const [detailEdgeId, setDetailEdgeId] = useState<string | null>(null);

  // ── Fetch each level ───────────────────────────────────────────

  const guidelineQuery = useQuery({
    queryKey: ["neighbors", guideline],
    queryFn: () => fetchNeighbors(guideline),
  });

  const recQuery = useQuery({
    queryKey: ["neighbors", rec],
    queryFn: () => fetchNeighbors(rec!),
    enabled: !!rec,
  });

  const strategyQuery = useQuery({
    queryKey: ["neighbors", strategy],
    queryFn: () => fetchNeighbors(strategy!),
    enabled: !!strategy,
  });

  // ── Build columns ─────────────────────────────────────────────

  const guidelineNodes: GraphNode[] = useMemo(() => {
    if (!guidelineQuery.data) return [];
    const center = guidelineQuery.data.nodes.find(
      (n) => n.id === guidelineQuery.data!.center,
    );
    return center ? [center] : [];
  }, [guidelineQuery.data]);

  const recNodes: GraphNode[] = useMemo(() => {
    if (!guidelineQuery.data) return [];
    return filterChildren(guidelineQuery.data.nodes, guideline);
  }, [guidelineQuery.data, guideline]);

  const strategyNodes: GraphNode[] = useMemo(() => {
    if (!rec || !recQuery.data) return [];
    return filterChildren(recQuery.data.nodes, rec);
  }, [rec, recQuery.data]);

  const actionNodes: GraphNode[] = useMemo(() => {
    if (!strategy || !strategyQuery.data) return [];
    return filterChildren(strategyQuery.data.nodes, strategy);
  }, [strategy, strategyQuery.data]);

  // Columns for the graph canvas.
  const canvasColumns: CanvasColumn[] = useMemo(() => {
    const cols: CanvasColumn[] = [
      { nodes: guidelineNodes, selectedId: guideline },
      { nodes: recNodes, selectedId: rec },
    ];
    if (rec) {
      cols.push({ nodes: strategyNodes, selectedId: strategy });
    }
    if (strategy) {
      cols.push({ nodes: actionNodes, selectedId: null });
    }
    return cols;
  }, [guidelineNodes, recNodes, strategyNodes, actionNodes, guideline, rec, strategy]);

  // ── Collect all edges across fetched subgraphs ─────────────────

  const allEdges: GraphEdge[] = useMemo(() => {
    const map = new Map<string, GraphEdge>();
    for (const q of [guidelineQuery, recQuery, strategyQuery]) {
      if (q.data) {
        for (const e of q.data.edges) {
          if (!map.has(e.id)) map.set(e.id, e);
        }
      }
    }
    return Array.from(map.values());
  }, [guidelineQuery.data, recQuery.data, strategyQuery.data]);

  // ── All nodes for detail panel lookup ──────────────────────────

  const allNodes: GraphNode[] = useMemo(() => {
    const map = new Map<string, GraphNode>();
    for (const q of [guidelineQuery, recQuery, strategyQuery]) {
      if (q.data) {
        for (const n of q.data.nodes) {
          if (!map.has(n.id)) map.set(n.id, n);
        }
      }
    }
    return Array.from(map.values());
  }, [guidelineQuery.data, recQuery.data, strategyQuery.data]);

  const detailNode = useMemo(
    () => (detailNodeId ? allNodes.find((n) => n.id === detailNodeId) ?? null : null),
    [allNodes, detailNodeId],
  );

  const detailEdge = useMemo(
    () => (detailEdgeId ? allEdges.find((e) => e.id === detailEdgeId) ?? null : null),
    [allEdges, detailEdgeId],
  );

  // ── Click handlers ─────────────────────────────────────────────

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setDetailNodeId(nodeId);
      setDetailEdgeId(null);

      // Find the node to determine its hierarchy level.
      const node = allNodes.find((n) => n.id === nodeId);
      if (!node) return;

      const rank = TYPE_RANK[node.labels[0]] ?? 99;

      switch (rank) {
        case 0: // Guideline
          setSelection(nodeId, null, null);
          break;
        case 1: // Recommendation
          setSelection(guideline, nodeId, null);
          break;
        case 2: // Strategy
          setSelection(guideline, rec, nodeId);
          break;
        default: // Action (Medication/Procedure/Observation) — detail only
          break;
      }
    },
    [allNodes, guideline, rec, setSelection],
  );

  const handleEdgeClick = useCallback(
    (edgeId: string) => {
      setDetailEdgeId(edgeId);
      setDetailNodeId(null);
    },
    [],
  );

  // Auto-select detail when URL state changes.
  useEffect(() => {
    if (strategy) setDetailNodeId(strategy);
    else if (rec) setDetailNodeId(rec);
    else setDetailNodeId(guideline);
  }, [guideline, rec, strategy]);

  const isLoading =
    guidelineQuery.isLoading ||
    (!!rec && recQuery.isLoading) ||
    (!!strategy && strategyQuery.isLoading);

  const error =
    guidelineQuery.error ?? recQuery.error ?? strategyQuery.error;

  return (
    <div className="flex h-full" data-testid="explore-page">
      {/* Center: graph canvas with column layout */}
      <div className="flex-1 min-w-0">
        {isLoading && allNodes.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-400">
            Loading graph...
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500 text-sm">
            Error: {(error as Error).message}
          </div>
        ) : (
          <GraphCanvas
            columns={canvasColumns}
            edges={allEdges}
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
