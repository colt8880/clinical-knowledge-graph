"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useQueries } from "@tanstack/react-query";
import { evaluate, fetchNeighbors } from "@/lib/api/client";
import type { PatientContext, GraphNode, GraphEdge } from "@/lib/api/client";
import {
  highlightedNodeIds as getHighlightedNodeIds,
  deriveRecommendations,
  clampIndex,
  subgraphFetchIds,
  visibleNodeIds,
} from "@/lib/eval/trace-nav";
import type { EvalTrace, TraceEvent } from "@/lib/eval/trace-nav";
import GraphCanvas, { type CanvasColumn } from "@/components/GraphCanvas";
import FixturePicker from "@/components/FixturePicker";
import TraceStepper from "@/components/TraceStepper";
import TraceEventList from "@/components/TraceEventList";
import RecommendationStrip from "@/components/RecommendationStrip";
import EventDetail from "@/components/EventDetail";

// Patient fixture JSONs are loaded statically at build time via dynamic import.
const FIXTURE_MODULES: Record<string, () => Promise<PatientContext>> = {
  "01-high-risk-55m-smoker": () =>
    import("../../../evals/fixtures/statins/01-high-risk-55m-smoker/patient.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "02-borderline-55f-sdm": () =>
    import("../../../evals/fixtures/statins/02-borderline-55f-sdm/patient.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "03-too-young-35m": () =>
    import("../../../evals/fixtures/statins/03-too-young-35m/patient.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "04-grade-i-78f": () =>
    import("../../../evals/fixtures/statins/04-grade-i-78f/patient.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "05-prior-mi-62m": () =>
    import("../../../evals/fixtures/statins/05-prior-mi-62m/patient.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
};

const GUIDELINE_ID = "guideline:uspstf-statin-2022";

export default function EvalPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-full text-slate-400">
          Loading...
        </div>
      }
    >
      <EvalContent />
    </Suspense>
  );
}

function EvalContent() {
  const searchParams = useSearchParams();

  const caseParam = searchParams.get("case");
  const seqParam = searchParams.get("seq");

  const [selectedFixture, setSelectedFixture] = useState<string | null>(
    caseParam,
  );
  const [trace, setTrace] = useState<EvalTrace | null>(null);
  const [currentIndex, setCurrentIndex] = useState<number>(
    seqParam ? parseInt(seqParam, 10) - 1 : 0,
  );
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Data fetching ──────────────────────────────────────────────

  // Always fetch the guideline subgraph (guideline + recs).
  const guidelineQuery = useQuery({
    queryKey: ["neighbors", GUIDELINE_ID],
    queryFn: () => fetchNeighbors(GUIDELINE_ID),
  });

  // From the full trace, determine which recs and strategies we need
  // neighbor data for. Fetches happen once when the trace loads.
  const events = useMemo(() => trace?.events ?? [], [trace]);
  const fetchIds = useMemo(() => subgraphFetchIds(events), [events]);

  // Fetch neighbors for each recommendation (gives us Strategy nodes).
  const recQueries = useQueries({
    queries: fetchIds.recIds.map((id) => ({
      queryKey: ["neighbors", id],
      queryFn: () => fetchNeighbors(id),
      staleTime: Infinity,
    })),
  });

  // Fetch neighbors for each strategy (gives us Action/Medication nodes).
  const strategyQueries = useQueries({
    queries: fetchIds.strategyIds.map((id) => ({
      queryKey: ["neighbors", id],
      queryFn: () => fetchNeighbors(id),
      staleTime: Infinity,
    })),
  });

  // ── URL state ─────────────────────────────────────────────────

  const updateUrl = useCallback(
    (fixtureId: string | null, seq: number | null) => {
      const params = new URLSearchParams();
      if (fixtureId) params.set("case", fixtureId);
      if (seq != null) params.set("seq", String(seq + 1));
      window.history.replaceState(null, "", `/eval?${params.toString()}`);
    },
    [],
  );

  const handleSelectFixture = useCallback(
    (fixtureId: string) => {
      setSelectedFixture(fixtureId);
      setTrace(null);
      setCurrentIndex(0);
      setError(null);
      updateUrl(fixtureId, null);
    },
    [updateUrl],
  );

  const handleRun = useCallback(async () => {
    if (!selectedFixture) return;
    const loader = FIXTURE_MODULES[selectedFixture];
    if (!loader) return;

    setIsRunning(true);
    setError(null);
    try {
      const patientContext = await loader();
      const result = await evaluate(patientContext);
      setTrace(result);
      setCurrentIndex(0);
      updateUrl(selectedFixture, 0);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsRunning(false);
    }
  }, [selectedFixture, updateUrl]);

  const handleSetIndex = useCallback(
    (index: number) => {
      const clamped = clampIndex(index, events.length);
      setCurrentIndex(clamped);
      updateUrl(selectedFixture, clamped);
    },
    [events.length, selectedFixture, updateUrl],
  );

  const handlePrev = useCallback(
    () => handleSetIndex(currentIndex - 1),
    [currentIndex, handleSetIndex],
  );
  const handleNext = useCallback(
    () => handleSetIndex(currentIndex + 1),
    [currentIndex, handleSetIndex],
  );

  // ── Current event + highlighting ──────────────────────────────

  const currentEvent: TraceEvent | null =
    events.length > 0 ? events[currentIndex] ?? null : null;

  const highlighted = useMemo(
    () => (currentEvent ? getHighlightedNodeIds(currentEvent) : []),
    [currentEvent],
  );

  const recommendations = useMemo(
    () => (trace ? deriveRecommendations(trace) : []),
    [trace],
  );

  // ── Build a complete node/edge pool from all fetched subgraphs ─

  const { nodePool, edgePool } = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();
    const edgeMap = new Map<string, GraphEdge>();

    const addSubgraph = (data: { nodes: GraphNode[]; edges: GraphEdge[] } | undefined) => {
      if (!data) return;
      for (const n of data.nodes) {
        if (!nodeMap.has(n.id)) nodeMap.set(n.id, n);
      }
      for (const e of data.edges) {
        if (!edgeMap.has(e.id)) edgeMap.set(e.id, e);
      }
    };

    addSubgraph(guidelineQuery.data);
    for (const q of recQueries) addSubgraph(q.data);
    for (const q of strategyQueries) addSubgraph(q.data);

    return {
      nodePool: nodeMap,
      edgePool: Array.from(edgeMap.values()),
    };
  }, [guidelineQuery.data, recQueries, strategyQueries]);

  // ── Build canvas columns based on which nodes the trace has visited ─

  const visible = useMemo(
    () => visibleNodeIds(events, currentIndex),
    [events, currentIndex],
  );

  const canvasColumns: CanvasColumn[] = useMemo(() => {
    if (!guidelineQuery.data) return [];

    const guidelineNode = nodePool.get(GUIDELINE_ID);
    if (!guidelineNode) return [];

    const cols: CanvasColumn[] = [
      { nodes: [guidelineNode], selectedId: null },
    ];

    // Col 1: Recommendations that have been considered up to currentIndex.
    const recNodes = Array.from(visible.recIds)
      .map((id) => nodePool.get(id))
      .filter((n): n is GraphNode => n != null);
    if (recNodes.length > 0) {
      cols.push({ nodes: recNodes, selectedId: null });
    }

    // Col 2: Strategies that have been considered.
    const strategyNodes = Array.from(visible.strategyIds)
      .map((id) => nodePool.get(id))
      .filter((n): n is GraphNode => n != null);
    if (strategyNodes.length > 0) {
      cols.push({ nodes: strategyNodes, selectedId: null });
    }

    // Col 3: Actions that have been checked.
    const actionNodes = Array.from(visible.actionIds)
      .map((id) => nodePool.get(id))
      .filter((n): n is GraphNode => n != null);
    if (actionNodes.length > 0) {
      cols.push({ nodes: actionNodes, selectedId: null });
    }

    return cols;
  }, [guidelineQuery.data, nodePool, visible]);

  // Only include edges between currently visible nodes.
  const visibleEdges = useMemo(() => {
    const visibleIds = new Set<string>();
    for (const col of canvasColumns) {
      for (const n of col.nodes) visibleIds.add(n.id);
    }
    return edgePool.filter(
      (e) => visibleIds.has(e.start) && visibleIds.has(e.end),
    );
  }, [canvasColumns, edgePool]);

  // ── Render ─────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full" data-testid="eval-page">
      {/* Top bar: fixture picker + run */}
      <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-slate-200 shrink-0">
        <FixturePicker
          selected={selectedFixture}
          onSelect={handleSelectFixture}
          disabled={isRunning}
        />
        <button
          className="px-4 py-1.5 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          onClick={handleRun}
          disabled={!selectedFixture || isRunning}
          data-testid="run-button"
        >
          {isRunning ? "Running..." : "Run"}
        </button>
        {error && (
          <span className="text-sm text-red-600">{error}</span>
        )}
      </div>

      {/* Main content area */}
      <div className="flex flex-1 min-h-0">
        {/* Left panel: stepper + event list */}
        <aside className="w-[340px] flex flex-col border-r border-slate-200 shrink-0 bg-white">
          {trace && (
            <>
              <TraceStepper
                currentIndex={currentIndex}
                totalEvents={events.length}
                onPrev={handlePrev}
                onNext={handleNext}
                onJump={handleSetIndex}
              />
              <TraceEventList
                events={events}
                currentIndex={currentIndex}
                onSelectIndex={handleSetIndex}
              />
            </>
          )}
          {!trace && !isRunning && (
            <div className="flex items-center justify-center h-full text-slate-400 text-sm">
              Select a fixture and click Run.
            </div>
          )}
        </aside>

        {/* Center: graph canvas */}
        <div className="flex-1 min-w-0">
          {guidelineQuery.isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              Loading graph...
            </div>
          ) : (
            <GraphCanvas
              columns={canvasColumns}
              edges={visibleEdges}
              highlightedNodeIds={highlighted}
            />
          )}
        </div>

        {/* Right panel: event detail */}
        <aside className="w-[380px] border-l border-slate-200 shrink-0 bg-slate-50 overflow-y-auto">
          <EventDetail event={currentEvent} />
        </aside>
      </div>

      {/* Bottom: recommendation strip */}
      {trace && <RecommendationStrip recommendations={recommendations} />}
    </div>
  );
}
