"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import type { GraphNode, GraphEdge } from "@/lib/api/client";

/**
 * A column of nodes to render in the graph canvas.
 * Nodes within a column are laid out vertically; columns progress left to right.
 */
export interface CanvasColumn {
  nodes: GraphNode[];
  selectedId: string | null;
}

interface GraphCanvasProps {
  /** Columns of nodes to lay out left-to-right. */
  columns: CanvasColumn[];
  /** Edges to draw between nodes across columns. */
  edges: GraphEdge[];
  /** Callback when a node is clicked. */
  onNodeClick?: (nodeId: string) => void;
  /** Callback when an edge is clicked. */
  onEdgeClick?: (edgeId: string) => void;
  /** Which node is selected (for detail panel highlight). */
  selectedNodeId?: string | null;
  /** Which edge is selected (for detail panel highlight). */
  selectedEdgeId?: string | null;
  /** Node ID(s) highlighted by the Eval tab stepper. */
  highlightedNodeIds?: string[];
}

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

const EDGE_COLORS: Record<string, string> = {
  FROM_GUIDELINE: "#6b21a8",
  OFFERS_STRATEGY: "#92400e",
  INCLUDES_ACTION: "#166534",
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

/** Layout constants. */
const COL_SPACING = 260;
const ROW_SPACING = 90;
const LEFT_PAD = 120;
const TOP_PAD = 80;

function buildElements(
  columns: CanvasColumn[],
  edges: GraphEdge[],
): ElementDefinition[] {
  const els: ElementDefinition[] = [];
  const nodeIds = new Set<string>();

  for (let col = 0; col < columns.length; col++) {
    const { nodes, selectedId } = columns[col];
    const colX = LEFT_PAD + col * COL_SPACING;
    // Center the column vertically.
    const totalHeight = (nodes.length - 1) * ROW_SPACING;
    const startY = TOP_PAD + Math.max(0, (300 - totalHeight) / 2);

    for (let row = 0; row < nodes.length; row++) {
      const n = nodes[row];
      nodeIds.add(n.id);
      const type = primaryLabel(n);
      const colors = TYPE_COLORS[type] ?? { bg: "#e2e8f0", border: "#64748b" };
      const display = nodeLabel(n);
      const nodeWidth = type === "Guideline" ? 180 : type === "Recommendation" ? 160 : 130;
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

  // Only include edges between nodes that are visible.
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
];

export default function GraphCanvas({
  columns,
  edges,
  onNodeClick,
  onEdgeClick,
  selectedNodeId,
  selectedEdgeId,
  highlightedNodeIds: highlightedIds,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  // Incremented each time cy is recreated so highlight effects re-fire.
  const [cyVersion, setCyVersion] = useState(0);

  const onNodeClickRef = useRef(onNodeClick);
  onNodeClickRef.current = onNodeClick;
  const onEdgeClickRef = useRef(onEdgeClick);
  onEdgeClickRef.current = onEdgeClick;

  const initCy = useCallback(() => {
    if (!containerRef.current) return;

    const elements = buildElements(columns, edges);

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: CY_STYLE,
      // Use preset layout — positions are set explicitly per node.
      layout: { name: "preset" },
      wheelSensitivity: 0.2,
      minZoom: 0.3,
      maxZoom: 2.5,
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
    });

    // Fit with padding after render.
    cy.fit(undefined, 40);

    cy.on("tap", "node", (evt) => {
      onNodeClickRef.current?.(evt.target.id());
    });

    cy.on("tap", "edge", (evt) => {
      onEdgeClickRef.current?.(evt.target.id());
    });

    cyRef.current = cy;
    setCyVersion((v) => v + 1);
  }, [columns, edges]);

  useEffect(() => {
    initCy();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [initCy]);

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

  // Eval tab: highlight node(s) for the current trace step.
  // Depends on cyVersion so it re-fires after cy is recreated (column expansion).
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
    <div
      ref={containerRef}
      className="w-full h-full bg-white"
      data-testid="graph-canvas"
    />
  );
}
