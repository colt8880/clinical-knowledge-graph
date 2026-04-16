"use client";

import { useEffect, useRef, useCallback } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import type { GraphNode, GraphEdge } from "@/lib/api/client";

// cose-bilkent is a UMD module; register it once on first import.
let coseBilkentRegistered = false;

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  highlight?: { nodeIds?: string[]; edgeIds?: string[] };
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  selectedNodeId?: string | null;
}

/** Color palette matching the crc-graph.html reference, keyed by Neo4j label. */
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
  FOR_CONDITION: "#64748b",
  OFFERS_STRATEGY: "#92400e",
  INCLUDES_ACTION: "#166534",
  EXCLUDED_BY: "#991b1b",
  TRIGGERED_BY: "#3730a3",
  TRIGGERS_FOLLOWUP: "#1e40af",
  PREEMPTED_BY: "#b91c1c",
};

function nodeLabel(node: GraphNode): string {
  const props = node.properties;
  return (
    (props.title as string) ??
    (props.name as string) ??
    (props.display_name as string) ??
    node.id
  );
}

function primaryLabel(node: GraphNode): string {
  return node.labels[0] ?? "Unknown";
}

/** Compute a font size that fits the label inside the node width. */
function computeFontSize(label: string, nodeWidth: number): number {
  // Rough heuristic: ~6px per character at font-size 10.
  // Allow text wrapping at ~nodeWidth, so measure the longest word.
  const words = label.split(/\s+/);
  const longestWord = words.reduce((a, b) => (a.length > b.length ? a : b), "");
  const charWidthAtSize10 = 6;
  const maxFontForLongestWord = Math.floor(
    (nodeWidth - 16) / (longestWord.length * (charWidthAtSize10 / 10)),
  );
  // Also consider total lines: if many words, shrink a bit.
  const totalChars = label.length;
  const charsPerLine = Math.floor((nodeWidth - 16) / charWidthAtSize10);
  const estimatedLines = Math.ceil(totalChars / charsPerLine);
  const maxFontForHeight = estimatedLines > 4 ? 8 : estimatedLines > 3 ? 9 : 10;

  return Math.max(7, Math.min(maxFontForLongestWord, maxFontForHeight, 11));
}

function toElements(
  nodes: GraphNode[],
  edges: GraphEdge[],
): ElementDefinition[] {
  const els: ElementDefinition[] = [];
  for (const n of nodes) {
    const label = primaryLabel(n);
    const colors = TYPE_COLORS[label] ?? { bg: "#e2e8f0", border: "#64748b" };
    const displayLabel = nodeLabel(n);
    const nodeWidth =
      label === "Guideline" ? 180 :
      label === "Recommendation" ? 150 :
      110;
    const fontSize = computeFontSize(displayLabel, nodeWidth);
    els.push({
      data: {
        id: n.id,
        label: displayLabel,
        nodeType: label,
        bgColor: colors.bg,
        borderColor: colors.border,
        nodeWidth,
        nodeHeight: label === "Guideline" ? 65 : label === "Recommendation" ? 70 : 55,
        fontSize,
      },
    });
  }
  for (const e of edges) {
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
        `${ele.data("nodeWidth") - 16}px`,
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
    selector: "edge[edgeType = 'EXCLUDED_BY']",
    style: { "line-style": "dashed" },
  },
  {
    selector: ".highlighted",
    style: {
      "overlay-color": "#0ea5e9",
      "overlay-opacity": 0.22,
      "overlay-padding": 8,
    },
  },
  {
    selector: ".selected-node",
    style: {
      "border-width": 3,
      "border-color": "#0ea5e9",
      "overlay-color": "#0ea5e9",
      "overlay-opacity": 0.12,
      "overlay-padding": 6,
    },
  },
];

export default function GraphCanvas({
  nodes,
  edges,
  highlight,
  onNodeClick,
  onEdgeClick,
  selectedNodeId,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Stable callback refs to avoid re-binding events.
  const onNodeClickRef = useRef(onNodeClick);
  onNodeClickRef.current = onNodeClick;
  const onEdgeClickRef = useRef(onEdgeClick);
  onEdgeClickRef.current = onEdgeClick;

  const initCy = useCallback(async () => {
    if (!containerRef.current) return;

    // Dynamically import and register cose-bilkent layout.
    if (!coseBilkentRegistered) {
      const coseBilkent = await import("cytoscape-cose-bilkent");
      cytoscape.use(coseBilkent.default ?? coseBilkent);
      coseBilkentRegistered = true;
    }

    const elements = toElements(nodes, edges);

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: CY_STYLE,
      layout: {
        name: "cose-bilkent",
        // Fixed seed for deterministic layout (per ISSUES.md).
        // @ts-expect-error — cose-bilkent options not in base types
        randomize: true,
        seed: 42,
        idealEdgeLength: 120,
        nodeRepulsion: 6000,
        animate: false,
      },
      wheelSensitivity: 0.2,
      minZoom: 0.15,
      maxZoom: 3,
    });

    cy.on("tap", "node", (evt) => {
      const id = evt.target.id();
      onNodeClickRef.current?.(id);
    });

    cy.on("tap", "edge", (evt) => {
      const id = evt.target.id();
      onEdgeClickRef.current?.(id);
    });

    cyRef.current = cy;
  }, [nodes, edges]);

  // Initialize / re-initialize when nodes or edges change.
  useEffect(() => {
    initCy();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [initCy]);

  // Apply highlight classes.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("highlighted");
    if (highlight?.nodeIds) {
      for (const id of highlight.nodeIds) {
        cy.getElementById(id).addClass("highlighted");
      }
    }
    if (highlight?.edgeIds) {
      for (const id of highlight.edgeIds) {
        cy.getElementById(id).addClass("highlighted");
      }
    }
  }, [highlight]);

  // Apply selected-node class.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("selected-node");
    if (selectedNodeId) {
      cy.getElementById(selectedNodeId).addClass("selected-node");
    }
  }, [selectedNodeId]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-white"
      data-testid="graph-canvas"
    />
  );
}
