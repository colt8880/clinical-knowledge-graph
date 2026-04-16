"use client";

import { Suspense, useCallback, useMemo, useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { fetchNeighbors } from "@/lib/api/client";
import type { GraphNode } from "@/lib/api/client";
import ColumnBrowser, {
  type Column,
  getColumnLabel,
  filterChildren,
} from "@/components/ColumnBrowser";
import NodeDetail from "@/components/NodeDetail";

const DEFAULT_GUIDELINE = "guideline:uspstf-statin-2022";

/**
 * The hierarchy has up to 4 levels:
 *   0: Guidelines
 *   1: Recommendations  (children of a Guideline)
 *   2: Strategies        (children of a Recommendation)
 *   3: Actions           (children of a Strategy — Medications/Procedures/Observations)
 *
 * URL state: ?g=<guideline>&r=<rec>&s=<strategy>
 * Each param records which node is selected at that level.
 * Columns to the right of the deepest selection are not shown.
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

  // Detail panel: which node is inspected (click selects in column, double-click or single-click shows detail).
  const [detailNodeId, setDetailNodeId] = useState<string | null>(null);

  // ── Fetch each level ───────────────────────────────────────────

  // Level 0: Guideline's neighbors → get Recommendations.
  const guidelineQuery = useQuery({
    queryKey: ["neighbors", guideline],
    queryFn: () => fetchNeighbors(guideline),
  });

  // Level 1: Selected Recommendation's neighbors → get Strategies.
  const recQuery = useQuery({
    queryKey: ["neighbors", rec],
    queryFn: () => fetchNeighbors(rec!),
    enabled: !!rec,
  });

  // Level 2: Selected Strategy's neighbors → get Actions.
  const strategyQuery = useQuery({
    queryKey: ["neighbors", strategy],
    queryFn: () => fetchNeighbors(strategy!),
    enabled: !!strategy,
  });

  // ── Build columns ─────────────────────────────────────────────

  // Column 0: Guidelines (just the one for v0).
  const guidelineNodes: GraphNode[] = useMemo(() => {
    if (!guidelineQuery.data) return [];
    const center = guidelineQuery.data.nodes.find(
      (n) => n.id === guidelineQuery.data!.center,
    );
    return center ? [center] : [];
  }, [guidelineQuery.data]);

  // Column 1: Recommendations (children of the guideline).
  const recNodes: GraphNode[] = useMemo(() => {
    if (!guidelineQuery.data) return [];
    return filterChildren(guidelineQuery.data.nodes, guideline);
  }, [guidelineQuery.data, guideline]);

  // Column 2: Strategies (children of the selected rec).
  const strategyNodes: GraphNode[] = useMemo(() => {
    if (!rec || !recQuery.data) return [];
    return filterChildren(recQuery.data.nodes, rec);
  }, [rec, recQuery.data]);

  // Column 3: Actions (children of the selected strategy).
  const actionNodes: GraphNode[] = useMemo(() => {
    if (!strategy || !strategyQuery.data) return [];
    return filterChildren(strategyQuery.data.nodes, strategy);
  }, [strategy, strategyQuery.data]);

  // Assemble the visible columns.
  const columns: Column[] = useMemo(() => {
    const cols: Column[] = [
      {
        label: getColumnLabel(guidelineNodes),
        nodes: guidelineNodes,
        selectedId: guideline,
      },
      {
        label: getColumnLabel(recNodes),
        nodes: recNodes,
        selectedId: rec,
      },
    ];

    // Show strategies column only when a rec is selected.
    if (rec) {
      cols.push({
        label: getColumnLabel(strategyNodes),
        nodes: strategyNodes,
        selectedId: strategy,
      });
    }

    // Show actions column only when a strategy is selected.
    if (strategy) {
      cols.push({
        label: getColumnLabel(actionNodes),
        nodes: actionNodes,
        selectedId: null,
      });
    }

    return cols;
  }, [
    guidelineNodes,
    recNodes,
    strategyNodes,
    actionNodes,
    guideline,
    rec,
    strategy,
  ]);

  // ── All fetched nodes (for detail panel lookup) ────────────────

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
    () => allNodes.find((n) => n.id === detailNodeId) ?? null,
    [allNodes, detailNodeId],
  );

  // ── Selection handler ──────────────────────────────────────────

  const handleSelect = useCallback(
    (columnIndex: number, nodeId: string) => {
      // Always show detail for the clicked node.
      setDetailNodeId(nodeId);

      switch (columnIndex) {
        case 0:
          // Clicking a guideline — reset everything below.
          setSelection(nodeId, null, null);
          break;
        case 1:
          // Clicking a rec — keep guideline, set rec, clear strategy.
          setSelection(guideline, nodeId, null);
          break;
        case 2:
          // Clicking a strategy — keep guideline + rec, set strategy.
          setSelection(guideline, rec, nodeId);
          break;
        case 3:
          // Clicking an action — just show detail, no deeper level.
          break;
      }
    },
    [guideline, rec, setSelection],
  );

  // Show detail when URL state changes selections.
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
      {/* Column browser — the primary navigation */}
      <div className="flex-1 min-w-0 flex">
        {isLoading && allNodes.length === 0 ? (
          <div className="flex items-center justify-center w-full text-slate-400">
            Loading graph...
          </div>
        ) : error ? (
          <div className="flex items-center justify-center w-full text-red-500 text-sm">
            Error: {(error as Error).message}
          </div>
        ) : (
          <ColumnBrowser
            columns={columns}
            onSelect={handleSelect}
            onNodeDetail={setDetailNodeId}
            detailNodeId={detailNodeId}
          />
        )}
      </div>

      {/* Right: detail panel */}
      <aside className="w-[420px] bg-slate-50 border-l border-slate-200 overflow-y-auto shrink-0">
        <NodeDetail node={detailNode} edge={null} />
      </aside>
    </div>
  );
}
