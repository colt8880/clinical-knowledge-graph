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
import GraphCanvas, { type CanvasColumn, type RecState } from "@/components/GraphCanvas";
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
  "cross-01-ascvd-62m": () =>
    import("../../../evals/fixtures/cross-domain/case-01/patient-context.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "cross-02-primary-55m": () =>
    import("../../../evals/fixtures/cross-domain/case-02/patient-context.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "cross-03-ckd3b-65m": () =>
    import("../../../evals/fixtures/cross-domain/case-03/patient-context.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
  "cross-04-ckd3a-55m": () =>
    import("../../../evals/fixtures/cross-domain/case-04/patient-context.json").then(
      (m) => m.default as unknown as PatientContext,
    ),
};

const DEFAULT_GUIDELINE_ID = "guideline:uspstf-statin-2022";

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

  // ── Data fetching ───────────────────────────────���──────────────

  // Determine guidelines from trace; fall back to default.
  const events = useMemo(() => trace?.events ?? [], [trace]);
  const guidelineIds = useMemo(() => {
    const ids = new Set<string>();
    for (const e of events) {
      if (e.type === "guideline_entered") ids.add(e.guideline_id);
    }
    return ids.size > 0 ? Array.from(ids) : [DEFAULT_GUIDELINE_ID];
  }, [events]);

  // Fetch the subgraph for each guideline (guideline + recs).
  const guidelineQueries = useQueries({
    queries: guidelineIds.map((id) => ({
      queryKey: ["neighbors", id],
      queryFn: () => fetchNeighbors(id),
      staleTime: Infinity,
    })),
  });
  const guidelineDataReady = guidelineQueries.some((q) => q.data != null);
  const guidelineDataLoading = guidelineQueries.some((q) => q.isLoading);

  // From the full trace, determine which recs and strategies we need
  // neighbor data for. Fetches happen once when the trace loads.
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

  // Derive preemption/modifier state from recommendations for canvas styling.
  const recState: RecState | undefined = useMemo(() => {
    if (recommendations.length === 0) return undefined;
    const preemptedBy = new Map<string, string>();
    const modifierCounts = new Map<string, number>();
    for (const rec of recommendations) {
      if (rec.preempted_by) {
        preemptedBy.set(rec.recommendation_id, rec.preempted_by);
      }
      if (rec.modifiers && rec.modifiers.length > 0) {
        modifierCounts.set(rec.recommendation_id, rec.modifiers.length);
      }
    }
    if (preemptedBy.size === 0 && modifierCounts.size === 0) return undefined;
    return { preemptedBy, modifierCounts };
  }, [recommendations]);

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

    for (const q of guidelineQueries) addSubgraph(q.data);
    for (const q of recQueries) addSubgraph(q.data);
    for (const q of strategyQueries) addSubgraph(q.data);

    return {
      nodePool: nodeMap,
      edgePool: Array.from(edgeMap.values()),
    };
  }, [guidelineQueries, recQueries, strategyQueries]);

  // ── Build canvas columns based on which nodes the trace has visited ─

  const visible = useMemo(
    () => visibleNodeIds(events, currentIndex),
    [events, currentIndex],
  );

  const canvasColumns: CanvasColumn[] = useMemo(() => {
    if (!guidelineDataReady) return [];

    // Guideline column: one node per guideline in the trace.
    const guidelineNodes = guidelineIds
      .map((id) => nodePool.get(id))
      .filter((n): n is GraphNode => n != null);
    if (guidelineNodes.length === 0) return [];

    const cols: CanvasColumn[] = [
      { nodes: guidelineNodes, selectedId: null },
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
  }, [guidelineDataReady, guidelineIds, nodePool, visible]);

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
                currentEventType={currentEvent?.type ?? null}
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
          {guidelineDataLoading ? (
            <div className="flex items-center justify-center h-full text-slate-400">
              Loading graph...
            </div>
          ) : (
            <GraphCanvas
              columns={canvasColumns}
              edges={visibleEdges}
              highlightedNodeIds={highlighted}
              recState={recState}
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
