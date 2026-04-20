"use client";

import { useEffect, useRef, useCallback, useState, useMemo } from "react";
import cytoscape, { type Core } from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import type { InteractionsResponse } from "@/lib/api/client";
import type { EdgeTypeFilter } from "@/lib/interactions/collapse";
import { collapseInteractions } from "@/lib/interactions/collapse";
import { INTERACTIONS_LAYOUT_OPTIONS } from "@/lib/interactions/layout";

if (typeof window !== "undefined") {
  try {
    cytoscape.use(coseBilkent);
  } catch {
    // Already registered.
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CY_STYLE: any[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-wrap": "wrap",
      "text-max-width": "160px",
      "text-valign": "center",
      "text-halign": "center",
      "font-size": 10,
      "font-weight": 500,
      width: (ele: { data: (k: string) => number }) => ele.data("nodeWidth") || 180,
      height: (ele: { data: (k: string) => number }) => ele.data("nodeHeight") || 60,
      shape: "round-rectangle",
      "border-width": 2,
      color: "#0f172a",
      "background-color": "data(bgColor)",
      "border-color": "data(borderColor)",
    },
  },
  // Cluster parents (compound nodes).
  {
    selector: "node[nodeType = '__interactions_cluster']",
    style: {
      "background-opacity": 0.08,
      "border-width": 2,
      "border-style": "dashed",
      "border-color": "data(borderColor)",
      "text-valign": "top",
      "text-halign": "center",
      "font-size": 13,
      "font-weight": 600,
      color: "data(borderColor)",
      padding: "35px",
    },
  },
  // Preempted rec: dimmed, dashed outline.
  {
    selector: "node[isPreempted = 'true']",
    style: {
      opacity: 0.4,
      "border-style": "dashed",
      "border-width": 2,
      "border-color": "#dc2626",
    },
  },
  // Rec with modifiers: amber border.
  {
    selector: "node[hasModifiers = 'true']",
    style: {
      "border-width": 3,
      "border-color": "#d97706",
    },
  },
  // Edges — base style with label and wide click target.
  {
    selector: "edge",
    style: {
      label: "data(edgeType)",
      "font-size": 8,
      color: "#64748b",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.9,
      "text-background-padding": "2px",
      width: 2,
      "line-color": "data(lineColor)",
      "target-arrow-color": "data(lineColor)",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "arrow-scale": 1,
      // Wide overlay for easier click targeting.
      "overlay-padding": 12,
    },
  },
  // PREEMPTED_BY edges: solid red, thicker.
  {
    selector: "edge[edgeType = 'PREEMPTED_BY']",
    style: {
      width: 3,
      "line-color": "#991b1b",
      "target-arrow-color": "#991b1b",
      "arrow-scale": 1.2,
    },
  },
  // MODIFIES edges: dotted amber.
  {
    selector: "edge[edgeType = 'MODIFIES']",
    style: {
      width: 2,
      "line-style": "dotted",
      "line-color": "#d97706",
      "target-arrow-color": "#d97706",
    },
  },
  // Suppressed modifier: reduced opacity.
  {
    selector: "edge[suppressed = 'true']",
    style: {
      opacity: 0.5,
      "line-dash-pattern": [4, 2],
    },
  },
  // Selected edge highlight.
  {
    selector: ".selected-edge",
    style: {
      width: 5,
      "overlay-color": "#0ea5e9",
      "overlay-opacity": 0.2,
      "overlay-padding": 8,
      "font-weight": 700,
    },
  },
  // Selected/focused node.
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
];

interface InteractionsCanvasProps {
  data: InteractionsResponse;
  edgeTypeFilter: EdgeTypeFilter;
  visibleGuidelines?: Set<string>;
  focusNodeId?: string | null;
  selectedNodeId?: string | null;
  selectedEdgeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
  onBackgroundClick?: () => void;
}

export default function InteractionsCanvas({
  data,
  edgeTypeFilter,
  visibleGuidelines,
  focusNodeId,
  selectedNodeId,
  selectedEdgeId,
  onNodeClick,
  onEdgeClick,
  onBackgroundClick,
}: InteractionsCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [cyVersion, setCyVersion] = useState(0);

  const onNodeClickRef = useRef(onNodeClick);
  onNodeClickRef.current = onNodeClick;
  const onEdgeClickRef = useRef(onEdgeClick);
  onEdgeClickRef.current = onEdgeClick;
  const onBackgroundClickRef = useRef(onBackgroundClick);
  onBackgroundClickRef.current = onBackgroundClick;

  // Memoize elements so cy only rebuilds when data or filter actually change.
  const elements = useMemo(
    () => collapseInteractions(data, edgeTypeFilter, visibleGuidelines).elements,
    [data, edgeTypeFilter, visibleGuidelines],
  );

  // Stable JSON key for initCy dependency — avoids new-reference-every-render.
  const elementsKey = useMemo(
    () => JSON.stringify(elements.map((e) => e.data.id)),
    [elements],
  );

  const initCy = useCallback(() => {
    if (!containerRef.current) return;

    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: CY_STYLE,
      layout: INTERACTIONS_LAYOUT_OPTIONS,
      wheelSensitivity: 0.2,
      minZoom: 0.5,
      maxZoom: 2.5,
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
      autoungrabify: false,
    });

    cy.fit(undefined, 50);

    cy.on("tap", "node", (evt) => {
      onNodeClickRef.current?.(evt.target.id());
    });

    cy.on("tap", "edge", (evt) => {
      onEdgeClickRef.current?.(evt.target.id());
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        onBackgroundClickRef.current?.();
      }
    });

    cyRef.current = cy;
    setCyVersion((v) => v + 1);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elementsKey]);

  useEffect(() => {
    initCy();
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [initCy]);

  // Focus node.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.elements().removeClass("focus-ring");

    if (focusNodeId) {
      const node = cy.getElementById(focusNodeId);
      if (node.length > 0) {
        node.addClass("focus-ring");
        cy.animate({
          center: { eles: node },
          zoom: 1.5,
          duration: 300,
        });
      }
    }
  }, [focusNodeId, cyVersion]);

  // Selected edge highlight.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("selected-edge");
    if (selectedEdgeId) {
      cy.getElementById(selectedEdgeId).addClass("selected-edge");
    }
  }, [selectedEdgeId, cyVersion]);

  // Selected node highlight.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (selectedNodeId && selectedNodeId !== focusNodeId) {
      cy.getElementById(selectedNodeId).addClass("focus-ring");
    }
  }, [selectedNodeId, focusNodeId, cyVersion]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-white"
      data-testid="interactions-canvas"
    />
  );
}
