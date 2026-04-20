"use client";

import { useMemo, useCallback, useState, useEffect } from "react";
import Link from "next/link";
import type { ForestNode } from "@/lib/api/client";
import type { ScopedSubgraph } from "@/lib/explore/scopedSubgraph";
import GraphCanvas, { nodeType } from "@/components/GraphCanvas";
import NodeDetail from "@/components/NodeDetail";

interface LogicViewProps {
  scoped: ScopedSubgraph;
  focusNodeId: string | null;
  onFocusChange: (nodeId: string | null) => void;
}

export default function LogicView({
  scoped,
  focusNodeId,
  onFocusChange,
}: LogicViewProps) {
  const [detailNodeId, setDetailNodeId] = useState<string | null>(null);
  const [detailEdgeId, setDetailEdgeId] = useState<string | null>(null);
  // Progressive drill-down: click a Strategy to reveal its Actions.
  const [expandedStrategyId, setExpandedStrategyId] = useState<string | null>(null);

  // Sync focus from URL.
  useEffect(() => {
    if (focusNodeId && !detailNodeId) {
      setDetailNodeId(focusNodeId);
    }
  }, [focusNodeId, detailNodeId]);

  const detailNode = useMemo(() => {
    const id = detailNodeId;
    if (!id) return null;
    return scoped.nodes.find((n) => n.id === id) ?? null;
  }, [scoped.nodes, detailNodeId]);

  const detailEdge = useMemo(
    () =>
      detailEdgeId
        ? scoped.edges.find((e) => e.id === detailEdgeId) ?? null
        : null,
    [scoped.edges, detailEdgeId],
  );

  // Build edge index for drill-down.
  const edgeIndex = useMemo(() => {
    const bySource = new Map<string, { type: string; target: string }[]>();
    for (const e of scoped.edges) {
      const list = bySource.get(e.start) ?? [];
      list.push({ type: e.type, target: e.end });
      bySource.set(e.start, list);
    }
    return bySource;
  }, [scoped.edges]);

  // Build column layout: Guideline → Recommendations → Strategies → Actions (on click).
  const { columns, visibleEdges } = useMemo(() => {
    const cols: ForestNode[][] = [[], [], [], []];
    const visibleIds = new Set<string>();

    const nodeById = new Map<string, ForestNode>();
    for (const n of scoped.nodes) nodeById.set(n.id, n);

    // Col 0: Guidelines, Col 1: Recommendations.
    for (const n of scoped.nodes) {
      const type = nodeType(n);
      if (type === "Guideline") {
        cols[0].push(n);
        visibleIds.add(n.id);
      } else if (type === "Recommendation") {
        cols[1].push(n);
        visibleIds.add(n.id);
      }
    }

    // Col 2: All strategies (always visible in scoped view).
    for (const n of scoped.nodes) {
      if (nodeType(n) === "Strategy") {
        cols[2].push(n);
        visibleIds.add(n.id);
      }
    }

    // Col 3: Actions only for the expanded Strategy.
    if (expandedStrategyId) {
      const targets = edgeIndex.get(expandedStrategyId) ?? [];
      for (const { type, target } of targets) {
        if (type === "INCLUDES_ACTION") {
          const node = nodeById.get(target);
          if (node) {
            cols[3].push(node);
            visibleIds.add(node.id);
          }
        }
      }
      visibleIds.add(expandedStrategyId);
    }

    const canvasColumns = cols.map((nodes) => ({
      nodes,
      selectedId: detailNodeId,
    }));

    // Collect strategy IDs so we can filter INCLUDES_ACTION edges
    // to only the expanded strategy.
    const strategyIds = new Set<string>();
    for (const n of scoped.nodes) {
      if (nodeType(n) === "Strategy") strategyIds.add(n.id);
    }

    const edges = scoped.edges.filter((e) => {
      if (!visibleIds.has(e.start) || !visibleIds.has(e.end)) return false;
      // Only show INCLUDES_ACTION edges from the expanded strategy.
      if (e.type === "INCLUDES_ACTION" && strategyIds.has(e.start)) {
        return e.start === expandedStrategyId;
      }
      return true;
    });

    return { columns: canvasColumns, visibleEdges: edges };
  }, [scoped, detailNodeId, expandedStrategyId, edgeIndex]);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setDetailNodeId(nodeId);
      setDetailEdgeId(null);
      onFocusChange(nodeId);

      // Progressive drill-down: clicking a Strategy expands its Actions.
      const node = scoped.nodes.find((n) => n.id === nodeId);
      if (node && nodeType(node) === "Strategy") {
        setExpandedStrategyId((prev) => (prev === nodeId ? null : nodeId));
      }
    },
    [onFocusChange, scoped.nodes],
  );

  const handleEdgeClick = useCallback((edgeId: string) => {
    setDetailEdgeId(edgeId);
    setDetailNodeId(null);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setDetailNodeId(null);
        setDetailEdgeId(null);
        setExpandedStrategyId(null);
        onFocusChange(null);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onFocusChange]);

  return (
    <div className="flex h-full" role="tabpanel" id="panel-logic" data-testid="logic-view">
      <div className="flex-1 min-w-0 relative">
        <GraphCanvas
          columns={columns}
          edges={visibleEdges}
          onNodeClick={handleNodeClick}
          onEdgeClick={handleEdgeClick}
          selectedNodeId={detailNodeId}
          selectedEdgeId={detailEdgeId}
        />

        {/* Cross-guideline badge overlay */}
        {scoped.crossGuidelineNodeIds.size > 0 && detailNodeId && scoped.crossGuidelineNodeIds.has(detailNodeId) && (
          <div className="absolute top-12 right-4 z-20">
            <Link
              href={`/interactions?focus=${encodeURIComponent(detailNodeId)}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-100 border border-amber-300 text-amber-800 text-xs font-medium hover:bg-amber-200 transition-colors"
              data-testid="cross-guideline-badge"
            >
              <span className="w-2 h-2 bg-amber-500 rounded-full" />
              Has cross-guideline interactions
            </Link>
          </div>
        )}
      </div>

      <aside className="w-[600px] bg-slate-50 border-l border-slate-200 overflow-y-auto shrink-0">
        <NodeDetail node={detailNode} edge={detailEdge} />
      </aside>
    </div>
  );
}
