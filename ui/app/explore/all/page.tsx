"use client";

import { Suspense, useCallback, useMemo, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSubgraph } from "@/lib/api/client";
import type { ForestNode, GraphEdge, GraphNode } from "@/lib/api/client";
import GraphCanvas, { type CanvasColumn, nodeType } from "@/components/GraphCanvas";
import DomainFilter from "@/components/DomainFilter";
import NodeDetail from "@/components/NodeDetail";
import {
  useExploreUrlState,
  domainKeysToApiLabels,
  type DomainKey,
} from "@/lib/explore/urlState";


export default function ExploreAllPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-slate-400">
          Loading...
        </div>
      }
    >
      <ExploreAllContent />
    </Suspense>
  );
}

function ExploreAllContent() {
  const { domains, focus, setDomains, setFocus } = useExploreUrlState();
  const [detailNodeId, setDetailNodeId] = useState<string | null>(null);
  const [detailEdgeId, setDetailEdgeId] = useState<string | null>(null);
  const [expandedRecId, setExpandedRecId] = useState<string | null>(null);
  const [expandedStrategyId, setExpandedStrategyId] = useState<string | null>(null);

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

  const visibleApiDomains = useMemo(
    () => new Set(domainKeysToApiLabels(domains).map((d) => d.toUpperCase().replace("-", "_"))),
    [domains],
  );

  const visibleNodes: ForestNode[] = useMemo(() => {
    return allNodes.filter((n) => {
      if (!n.domain) return true;
      return visibleApiDomains.has(n.domain);
    });
  }, [allNodes, visibleApiDomains]);

  const edgeIndex = useMemo(() => {
    const bySource = new Map<string, { type: string; target: string }[]>();
    for (const e of allEdges) {
      const list = bySource.get(e.start) ?? [];
      list.push({ type: e.type, target: e.end });
      bySource.set(e.start, list);
    }
    return bySource;
  }, [allEdges]);

  const { exploreColumns, visibleEdges } = useMemo(() => {
    const cols: GraphNode[][] = [[], [], [], []];
    const visibleIds = new Set<string>();
    const nodeById = new Map<string, ForestNode>();
    for (const n of visibleNodes) nodeById.set(n.id, n);

    for (const n of visibleNodes) {
      const type = nodeType(n);
      if (type === "Guideline") {
        cols[0].push(n);
        visibleIds.add(n.id);
      } else if (type === "Recommendation") {
        cols[1].push(n);
        visibleIds.add(n.id);
      }
    }

    if (expandedRecId) {
      const targets = edgeIndex.get(expandedRecId) ?? [];
      for (const { type, target } of targets) {
        if (type === "OFFERS_STRATEGY") {
          const node = nodeById.get(target);
          if (node) {
            cols[2].push(node);
            visibleIds.add(node.id);
          }
        }
      }
      visibleIds.add(expandedRecId);
    }

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

    const columns: CanvasColumn[] = cols.map((nodes) => ({
      nodes,
      selectedId: detailNodeId,
    }));

    const edges = allEdges.filter(
      (e) => visibleIds.has(e.start) && visibleIds.has(e.end),
    );

    return { exploreColumns: columns, visibleEdges: edges };
  }, [visibleNodes, allEdges, detailNodeId, expandedRecId, expandedStrategyId, edgeIndex]);

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

  useEffect(() => {
    if (focus && !detailNodeId) {
      setDetailNodeId(focus);
    }
  }, [focus, detailNodeId]);

  const handleNodeClick = useCallback(
    (nodeId: string) => {
      setDetailNodeId(nodeId);
      setDetailEdgeId(null);
      setFocus(nodeId);

      const node = allNodes.find((n) => n.id === nodeId);
      if (!node) return;
      const type = nodeType(node);

      if (type === "Recommendation") {
        setExpandedRecId((prev) => (prev === nodeId ? null : nodeId));
        setExpandedStrategyId(null);
      } else if (type === "Strategy") {
        setExpandedStrategyId((prev) => (prev === nodeId ? null : nodeId));
      }
    },
    [setFocus, allNodes],
  );

  const handleEdgeClick = useCallback((edgeId: string) => {
    setDetailEdgeId(edgeId);
    setDetailNodeId(null);
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setDetailNodeId(null);
    setDetailEdgeId(null);
    setExpandedRecId(null);
    setExpandedStrategyId(null);
    setFocus(null);
  }, [setFocus]);

  const handleDomainChange = useCallback(
    (newDomains: DomainKey[]) => {
      setDomains(newDomains);
    },
    [setDomains],
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setDetailNodeId(null);
        setDetailEdgeId(null);
        setExpandedRecId(null);
        setExpandedStrategyId(null);
        setFocus(null);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setFocus]);

  return (
    <div className="flex h-full" data-testid="explore-all-page">
      <aside className="w-[200px] bg-slate-50 border-r border-slate-200 shrink-0">
        <DomainFilter
          visibleDomains={domains}
          onChange={handleDomainChange}
        />
      </aside>

      <div
        className="flex-1 min-w-0 relative"
        onClick={(e) => {
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
            columns={exploreColumns}
            edges={visibleEdges}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            selectedNodeId={detailNodeId}
            selectedEdgeId={detailEdgeId}
          />
        )}
      </div>

      <aside className="w-[420px] bg-slate-50 border-l border-slate-200 overflow-y-auto shrink-0">
        <NodeDetail node={detailNode} edge={detailEdge} />
      </aside>
    </div>
  );
}
