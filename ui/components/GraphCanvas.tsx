"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import type { GraphNode, GraphEdge, ForestNode } from "@/lib/api/client";
import { DOMAIN_PARENTS, FOREST_LAYOUT_OPTIONS } from "@/lib/explore/layout";
import GraphTooltips from "./GraphTooltips";

// Register cose-bilkent layout once.
if (typeof window !== "undefined") {
  try {
    cytoscape.use(coseBilkent);
  } catch {
    // Already registered.
  }
}

/**
 * A column of nodes to render in the graph canvas (legacy Eval tab mode).
 * Nodes within a column are laid out vertically; columns progress left to right.
 */
export interface CanvasColumn {
  nodes: GraphNode[];
  selectedId: string | null;
}

/** Props for the legacy column-based layout (Eval tab). */
interface ColumnModeProps {
  columns: CanvasColumn[];
  edges: GraphEdge[];
  nodes?: undefined;
  visibleDomains?: undefined;
  focusedNodeId?: undefined;
}

/** Props for the whole-forest layout (Explore tab). */
interface ForestModeProps {
  nodes: ForestNode[];
  edges: GraphEdge[];
  columns?: undefined;
  visibleDomains?: string[];
  focusedNodeId?: string | null;
}

/** Preemption and modifier state derived from the trace's recommendations. */
export interface RecState {
  /** Map from rec ID to the winning rec ID, for preempted recs. */
  preemptedBy: Map<string, string>;
  /** Map from rec ID to modifier count, for recs with active modifiers. */
  modifierCounts: Map<string, number>;
}

type GraphCanvasProps = (ColumnModeProps | ForestModeProps) & {
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  selectedNodeId?: string | null;
  selectedEdgeId?: string | null;
  highlightedNodeIds?: string[];
  /** Preemption/modifier state from trace recommendations. */
  recState?: RecState;
};

/** Color palette keyed by Neo4j label. */
const TYPE_COLORS: Record<string, { bg: string; border: string }> = {
  Guideline: { bg: "#f3e8ff", border: "#6b21a8" },
  Recommendation: { bg: "#dbeafe", border: "#1e40af" },
  Strategy: { bg: "#fef3c7", border: "#92400e" },
  Condition: { bg: "#fee2e2", border: "#991b1b" },
  Procedure: { bg: "#dcfce7", border: "#166534" },
  Observation: { bg: "#e0e7ff", border: "#3730a3" },
  Medication: { bg: "#fce7f3", border: "#9d174d" },
};

/** Domain-specific Rec/Strategy coloring. */
const DOMAIN_COLORS: Record<string, { bg: string; border: string }> = {
  USPSTF: { bg: "#dbeafe", border: "#2563eb" },       // blue
  ACC_AHA: { bg: "#ede9fe", border: "#7c3aed" },      // purple
  KDIGO: { bg: "#d1fae5", border: "#059669" },         // green
};

const EDGE_COLORS: Record<string, string> = {
  FROM_GUIDELINE: "#6b21a8",
  OFFERS_STRATEGY: "#92400e",
  INCLUDES_ACTION: "#166534",
  PREEMPTED_BY: "#dc2626",
  MODIFIES: "#d97706",
  TARGETS: "#991b1b",
};

/** Domain-specific edge colors for intra-guideline edges. */
const DOMAIN_EDGE_COLORS: Record<string, string> = {
  USPSTF: "#2563eb",
  ACC_AHA: "#7c3aed",
  KDIGO: "#059669",
};

function nodeLabel(node: GraphNode): string {
  return (
    (node.properties.title as string) ??
    (node.properties.name as string) ??
    (node.properties.display_name as string) ??
    node.id
  );
}

function primaryLabel(node: GraphNode): string {
  return node.labels[0] ?? "Unknown";
}

function computeFontSize(label: string, nodeWidth: number): number {
  const words = label.split(/\s+/);
  const longestWord = words.reduce((a, b) => (a.length > b.length ? a : b), "");
  const charWidth = 6;
  const maxForWord = Math.floor(
    (nodeWidth - 20) / (longestWord.length * (charWidth / 10)),
  );
  const charsPerLine = Math.floor((nodeWidth - 20) / charWidth);
  const lines = Math.ceil(label.length / charsPerLine);
  const maxForHeight = lines > 4 ? 8 : lines > 3 ? 9 : 10;
  return Math.max(7, Math.min(maxForWord, maxForHeight, 11));
}

// ── Column-mode layout (Eval tab) ────────────────────────────────────
// Fixed 4-column layout: Guideline → Recommendation → Strategy → Action.
// Columns always occupy their position even when empty, so nodes never
// shift horizontally as the trace progresses.

const COL_SPACING = 280;
const ROW_SPACING = 80;
const LEFT_PAD = 100;
const TOP_PAD = 50;
const HEADER_Y = 20;

const COLUMN_HEADERS = ["Guidelines", "Recommendations", "Strategies", "Actions"];

function buildColumnElements(
  columns: CanvasColumn[],
  edges: GraphEdge[],
): ElementDefinition[] {
  const els: ElementDefinition[] = [];
  const nodeIds = new Set<string>();

  // Add column header labels as non-interactive nodes.
  for (let col = 0; col < columns.length; col++) {
    const colX = LEFT_PAD + col * COL_SPACING;
    const header = COLUMN_HEADERS[col] ?? `Column ${col}`;
    els.push({
      data: {
        id: `__header_${col}`,
        label: header,
        nodeType: "__header",
        bgColor: "transparent",
        borderColor: "transparent",
        nodeWidth: 200,
        nodeHeight: 24,
        fontSize: 11,
        isSelected: "false",
      },
      position: { x: colX, y: HEADER_Y },
    });
  }

  for (let col = 0; col < columns.length; col++) {
    const { nodes, selectedId } = columns[col];
    if (nodes.length === 0) continue;

    const colX = LEFT_PAD + col * COL_SPACING;
    const totalHeight = (nodes.length - 1) * ROW_SPACING;
    const startY = TOP_PAD + Math.max(0, (200 - totalHeight) / 2);

    for (let row = 0; row < nodes.length; row++) {
      const n = nodes[row];
      nodeIds.add(n.id);
      const type = primaryLabel(n);
      const colors = TYPE_COLORS[type] ?? { bg: "#e2e8f0", border: "#64748b" };
      const display = nodeLabel(n);
      const nodeWidth = type === "Guideline" ? 180 : type === "Recommendation" ? 170 : 140;
      const nodeHeight = type === "Guideline" ? 60 : 55;
      const isSelected = n.id === selectedId;

      els.push({
        data: {
          id: n.id,
          label: display,
          nodeType: type,
          bgColor: colors.bg,
          borderColor: colors.border,
          nodeWidth,
          nodeHeight,
          fontSize: computeFontSize(display, nodeWidth),
          isSelected: isSelected ? "true" : "false",
        },
        position: { x: colX, y: startY + row * ROW_SPACING },
      });
    }
  }

  for (const e of edges) {
    if (nodeIds.has(e.start) && nodeIds.has(e.end)) {
      els.push({
        data: {
          id: e.id,
          source: e.start,
          target: e.end,
          edgeType: e.type,
          lineColor: EDGE_COLORS[e.type] ?? "#94a3b8",
        },
      });
    }
  }

  return els;
}

// ── Forest-mode layout (Explore tab) ─────────────────────────────────

const GUIDELINE_SCOPED_TYPES = new Set(["Guideline", "Recommendation", "Strategy"]);

function buildForestElements(
  nodes: ForestNode[],
  edges: GraphEdge[],
): ElementDefinition[] {
  const els: ElementDefinition[] = [];
  const nodeIds = new Set<string>();

  // Add compound parent nodes for each domain cluster.
  const domainsPresent = Array.from(new Set(nodes.map((n) => n.domain).filter(Boolean) as string[]));
  for (const domain of domainsPresent) {
    const parentId = DOMAIN_PARENTS[domain];
    if (parentId) {
      const domainColors = DOMAIN_COLORS[domain] ?? { bg: "#f1f5f9", border: "#94a3b8" };
      els.push({
        data: {
          id: parentId,
          label: domain.replace("_", "/"),
          nodeType: "__cluster",
          bgColor: `${domainColors.bg}80`,
          borderColor: domainColors.border,
        },
      });
    }
  }

  for (const n of nodes) {
    nodeIds.add(n.id);
    const type = primaryLabel(n);
    const domain = n.domain;
    const isGuidelineScoped = domain != null && GUIDELINE_SCOPED_TYPES.has(type);

    // Domain-colored nodes for Rec/Strategy; TYPE_COLORS for shared entities.
    let colors: { bg: string; border: string };
    if (isGuidelineScoped && domain && DOMAIN_COLORS[domain]) {
      colors = DOMAIN_COLORS[domain];
    } else {
      colors = TYPE_COLORS[type] ?? { bg: "#e2e8f0", border: "#64748b" };
    }

    const display = nodeLabel(n);
    const nodeWidth = type === "Guideline" ? 180 : type === "Recommendation" ? 160 : 130;
    const nodeHeight = type === "Guideline" ? 60 : 55;

    // Domain badge text for Rec/Strategy nodes.
    const domainBadge = isGuidelineScoped && domain
      ? domain.replace("_", "/")
      : "";

    const data: Record<string, unknown> = {
      id: n.id,
      label: domainBadge ? `${domainBadge}\n${display}` : display,
      nodeType: type,
      bgColor: colors.bg,
      borderColor: colors.border,
      nodeWidth,
      nodeHeight,
      fontSize: computeFontSize(display, nodeWidth),
      isSelected: "false",
      domain: domain ?? "",
      is_cross_guideline: "false",
    };

    // Parent assignment for compound clustering.
    if (domain && DOMAIN_PARENTS[domain]) {
      data.parent = DOMAIN_PARENTS[domain];
    }

    els.push({ data });
  }

  // Build a lookup from node id to domain for edge coloring.
  const nodeIdToDomain = new Map<string, string | null>();
  for (const n of nodes) {
    nodeIdToDomain.set(n.id, n.domain);
  }

  for (const e of edges) {
    if (nodeIds.has(e.start) && nodeIds.has(e.end)) {
      const sourceDomain = nodeIdToDomain.get(e.start);
      const targetDomain = nodeIdToDomain.get(e.end);
      const isCrossGuideline =
        sourceDomain != null &&
        targetDomain != null &&
        sourceDomain !== targetDomain;

      // Intra-guideline edges inherit source domain color.
      let lineColor = EDGE_COLORS[e.type] ?? "#94a3b8";
      if (!isCrossGuideline && sourceDomain && DOMAIN_EDGE_COLORS[sourceDomain]) {
        lineColor = DOMAIN_EDGE_COLORS[sourceDomain];
      }

      els.push({
        data: {
          id: e.id,
          source: e.start,
          target: e.end,
          edgeType: e.type,
          lineColor,
          is_cross_guideline: isCrossGuideline ? "true" : "false",
        },
      });
    }
  }

  return els;
}

// ── Cytoscape style ─────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CY_STYLE: any[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-wrap": "wrap",
      "text-max-width": (ele: { data: (k: string) => number }) =>
        `${ele.data("nodeWidth") - 20}px`,
      "text-valign": "center",
      "text-halign": "center",
      "font-size": (ele: { data: (k: string) => number }) =>
        ele.data("fontSize"),
      "font-weight": 500,
      width: (ele: { data: (k: string) => number }) => ele.data("nodeWidth"),
      height: (ele: { data: (k: string) => number }) => ele.data("nodeHeight"),
      shape: "round-rectangle",
      "border-width": 2,
      color: "#0f172a",
      "background-color": "data(bgColor)",
      "border-color": "data(borderColor)",
    },
  },
  {
    selector: "node[nodeType = 'Guideline']",
    style: { "font-weight": 600 },
  },
  {
    selector: "node[nodeType = '__header']",
    style: {
      "background-opacity": 0,
      "border-width": 0,
      "font-size": 11,
      "font-weight": 600,
      "text-transform": "uppercase",
      color: "#94a3b8",
      "text-valign": "center",
      "text-halign": "center",
      "events": "no",
    },
  },
  {
    selector: "node[nodeType = '__cluster']",
    style: {
      "background-opacity": 0.08,
      "border-width": 2,
      "border-style": "dashed",
      "border-color": "data(borderColor)",
      "text-valign": "top",
      "text-halign": "center",
      "font-size": 12,
      "font-weight": 600,
      color: "data(borderColor)",
      padding: "30px",
    },
  },
  {
    selector: "node[isSelected = 'true']",
    style: {
      "border-width": 3,
      "border-color": "#0ea5e9",
      "overlay-color": "#0ea5e9",
      "overlay-opacity": 0.1,
      "overlay-padding": 4,
    },
  },
  {
    selector: "edge",
    style: {
      label: "data(edgeType)",
      "font-size": 8,
      color: "#64748b",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.9,
      "text-background-padding": "2px",
      width: 1.5,
      "line-color": "data(lineColor)",
      "target-arrow-color": "data(lineColor)",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "arrow-scale": 0.8,
    },
  },
  {
    selector: ".selected-edge",
    style: {
      "line-color": "#0ea5e9",
      "target-arrow-color": "#0ea5e9",
      width: 3,
    },
  },
  {
    selector: ".detail-node",
    style: {
      "border-width": 3,
      "border-color": "#6366f1",
      "overlay-color": "#6366f1",
      "overlay-opacity": 0.12,
      "overlay-padding": 5,
    },
  },
  {
    selector: ".eval-highlight",
    style: {
      "border-width": 3,
      "border-color": "#f59e0b",
      "overlay-color": "#f59e0b",
      "overlay-opacity": 0.15,
      "overlay-padding": 6,
    },
  },
  {
    selector: ".focus-ring",
    style: {
      "border-width": 3,
      "border-color": "#0ea5e9",
      "overlay-color": "#0ea5e9",
      "overlay-opacity": 0.15,
      "overlay-padding": 6,
    },
  },
  // Preempted node: dimmed opacity, dashed outline, label suffix handled in data.
  {
    selector: ".preempted",
    style: {
      opacity: 0.4,
      "border-style": "dashed",
      "border-width": 2,
    },
  },
  // PREEMPTED_BY edge: thicker stroke, desaturated red, prominent arrow.
  {
    selector: "edge[edgeType = 'PREEMPTED_BY']",
    style: {
      width: 3,
      "line-color": "#991b1b",
      "target-arrow-color": "#991b1b",
      "line-style": "solid",
      "arrow-scale": 1.2,
      "font-size": 9,
      "font-weight": 600,
    },
  },
  // MODIFIES edge: dotted line, amber color.
  {
    selector: "edge[edgeType = 'MODIFIES']",
    style: {
      width: 2,
      "line-color": "#d97706",
      "target-arrow-color": "#d97706",
      "line-style": "dotted",
      "arrow-scale": 0.9,
    },
  },
  // Modifier badge on target Rec (has modifiers).
  {
    selector: ".has-modifiers",
    style: {
      "border-width": 3,
      "border-color": "#d97706",
    },
  },
  // "Hidden by filter" indicator: node whose cross-guideline source is filtered out.
  {
    selector: ".cross-edge-filtered",
    style: {
      "border-style": "dotted",
      "border-color": "#94a3b8",
    },
  },
];

export default function GraphCanvas(props: GraphCanvasProps) {
  const {
    onNodeClick,
    onEdgeClick,
    selectedNodeId,
    selectedEdgeId,
    highlightedNodeIds: highlightedIds,
    recState,
  } = props;

  const isForestMode = props.nodes !== undefined;

  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [cyVersion, setCyVersion] = useState(0);

  const onNodeClickRef = useRef(onNodeClick);
  onNodeClickRef.current = onNodeClick;
  const onEdgeClickRef = useRef(onEdgeClick);
  onEdgeClickRef.current = onEdgeClick;

  // Build and mount Cytoscape instance.
  const initCy = useCallback(() => {
    if (!containerRef.current) return;

    let elements: ElementDefinition[];
    let layoutConfig: { name: string; [key: string]: unknown };

    if (isForestMode) {
      elements = buildForestElements(props.nodes!, props.edges);
      layoutConfig = { ...FOREST_LAYOUT_OPTIONS };
    } else {
      elements = buildColumnElements(props.columns!, props.edges);
      layoutConfig = { name: "preset" };
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: CY_STYLE,
      layout: layoutConfig,
      wheelSensitivity: 0.2,
      minZoom: 0.3,
      maxZoom: 2.5,
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
    });

    if (!isForestMode) {
      cy.fit(undefined, 40);
    }

    cy.on("tap", "node", (evt) => {
      const id = evt.target.id();
      // Don't fire for compound parent nodes or column headers.
      if (id.startsWith("__cluster_") || id.startsWith("__header_")) return;
      onNodeClickRef.current?.(id);
    });

    cy.on("tap", "edge", (evt) => {
      onEdgeClickRef.current?.(evt.target.id());
    });

    cyRef.current = cy;
    setCyVersion((v) => v + 1);
  // Deps: isForestMode determines which data path; nodes/columns/edges drive re-render.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isForestMode, props.nodes, props.columns, props.edges]);

  useEffect(() => {
    initCy();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [initCy]);

  // Forest mode: apply visibility filter based on visibleDomains.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isForestMode) return;

    const visibleDomains = props.visibleDomains;
    if (!visibleDomains) return;

    const visibleSet = new Set(
      visibleDomains.map((d) => d.toUpperCase().replace("-", "_")),
    );

    cy.nodes().forEach((node) => {
      const nodeType = node.data("nodeType");
      if (nodeType === "__cluster") {
        // Show/hide cluster parents based on domain.
        const clusterDomain = Object.entries(DOMAIN_PARENTS).find(
          ([, v]) => v === node.id(),
        )?.[0];
        if (clusterDomain) {
          if (visibleSet.has(clusterDomain)) {
            node.style("display", "element");
          } else {
            node.style("display", "none");
          }
        }
        return;
      }

      const domain = node.data("domain") as string;
      if (!domain) {
        // Shared entities always visible.
        node.style("display", "element");
      } else if (visibleSet.has(domain)) {
        node.style("display", "element");
      } else {
        node.style("display", "none");
      }
    });

    // Edges: hide when either endpoint is hidden; mark target Recs whose
    // cross-guideline source is filtered out with "cross-edge-filtered".
    cy.nodes().removeClass("cross-edge-filtered");
    cy.edges().forEach((edge) => {
      const src = cy.getElementById(edge.data("source"));
      const tgt = cy.getElementById(edge.data("target"));
      const srcHidden = src.style("display") === "none";
      const tgtHidden = tgt.style("display") === "none";
      if (srcHidden || tgtHidden) {
        edge.style("display", "none");
        // If this is a cross-guideline edge (PREEMPTED_BY or MODIFIES) and
        // only the source is hidden, mark the target with a filter indicator.
        const edgeType = edge.data("edgeType") as string;
        if (srcHidden && !tgtHidden && (edgeType === "PREEMPTED_BY" || edgeType === "MODIFIES")) {
          tgt.addClass("cross-edge-filtered");
        }
      } else {
        edge.style("display", "element");
      }
    });
  }, [isForestMode, props.visibleDomains, cyVersion]);

  // Forest mode: focus a specific node.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !isForestMode) return;

    cy.elements().removeClass("focus-ring");

    const focusId = props.focusedNodeId;
    if (focusId) {
      const node = cy.getElementById(focusId);
      if (node.length > 0) {
        node.addClass("focus-ring");
        cy.animate({
          center: { eles: node },
          zoom: 1.2,
          duration: 300,
        });
      }
    }
  }, [isForestMode, props.focusedNodeId, cyVersion]);

  // Highlight the node shown in the detail panel.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("detail-node");
    if (selectedNodeId) {
      cy.getElementById(selectedNodeId).addClass("detail-node");
    }
  }, [selectedNodeId]);

  // Highlight the edge shown in the detail panel.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("selected-edge");
    if (selectedEdgeId) {
      cy.getElementById(selectedEdgeId).addClass("selected-edge");
    }
  }, [selectedEdgeId]);

  // Track which nodes had their labels modified so we can restore them.
  const modifiedLabelsRef = useRef<Map<string, string>>(new Map());

  // Apply preemption/modifier classes from recState.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    // Restore any previously modified labels before reapplying.
    modifiedLabelsRef.current.forEach((originalLabel, nodeId) => {
      const node = cy.getElementById(nodeId);
      if (node.length > 0) {
        node.data("label", originalLabel);
      }
    });
    modifiedLabelsRef.current.clear();

    cy.nodes().removeClass("preempted has-modifiers");
    if (!recState) return;

    recState.preemptedBy.forEach((winnerId, recId) => {
      const node = cy.getElementById(recId);
      if (node.length > 0) {
        node.addClass("preempted");
        const label = node.data("label") as string;
        if (label) {
          modifiedLabelsRef.current.set(recId, label);
          node.data("label", `${label}\n(preempted by ${winnerId.split(":").pop()})`);
        }
      }
    });

    recState.modifierCounts.forEach((count, recId) => {
      if (count > 0) {
        const node = cy.getElementById(recId);
        if (node.length > 0) {
          node.addClass("has-modifiers");
          const label = node.data("label") as string;
          if (label) {
            // Only store original if not already stored by preemption above.
            if (!modifiedLabelsRef.current.has(recId)) {
              modifiedLabelsRef.current.set(recId, label);
            }
            node.data("label", `${node.data("label")}\n[mod: ${count}]`);
          }
        }
      }
    });
  }, [recState, cyVersion]);

  // Eval tab: highlight node(s) for the current trace step.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("eval-highlight");
    if (highlightedIds && highlightedIds.length > 0) {
      for (const id of highlightedIds) {
        cy.getElementById(id).addClass("eval-highlight");
      }
    }
  }, [highlightedIds, cyVersion]);

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="w-full h-full bg-white"
        data-testid="graph-canvas"
      />
      <GraphTooltips cyRef={cyRef} cyVersion={cyVersion} />
    </div>
  );
}
