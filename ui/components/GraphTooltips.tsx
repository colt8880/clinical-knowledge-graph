"use client";

import { useEffect, useRef, useState } from "react";
import type { Core } from "cytoscape";

interface TooltipData {
  x: number;
  y: number;
  content: TooltipContent;
}

type TooltipContent =
  | { kind: "preemption"; edgePriority: string; reason: string }
  | { kind: "modifier"; nature: string; note: string; sourceGuideline: string }
  | { kind: "modifier-badge"; count: number };

interface GraphTooltipsProps {
  /** Ref to the Cytoscape core instance. */
  cyRef: React.RefObject<Core | null>;
  /** Version counter that increments when Cytoscape re-initializes. */
  cyVersion: number;
}

/**
 * Hover tooltip overlay for preemption edges, modifier edges, and modifier badges.
 * Renders as a positioned div overlaying the canvas container. Cytoscape events
 * drive tooltip visibility; React renders the content.
 */
export default function GraphTooltips({ cyRef, cyVersion }: GraphTooltipsProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const showEdgeTooltip = (evt: { target: { data: (k: string) => string }; renderedPosition: { x: number; y: number } }) => {
      const edgeType = evt.target.data("edgeType");
      const pos = evt.renderedPosition;
      if (edgeType === "PREEMPTED_BY") {
        setTooltip({
          x: pos.x,
          y: pos.y,
          content: {
            kind: "preemption",
            edgePriority: evt.target.data("edgePriority") ?? "—",
            reason: evt.target.data("edgeReason") ?? "—",
          },
        });
      } else if (edgeType === "MODIFIES") {
        setTooltip({
          x: pos.x,
          y: pos.y,
          content: {
            kind: "modifier",
            nature: evt.target.data("edgeNature") ?? "—",
            note: evt.target.data("edgeNote") ?? "—",
            sourceGuideline: evt.target.data("edgeSourceGuideline") ?? "—",
          },
        });
      }
    };

    const showNodeTooltip = (evt: { target: { hasClass: (c: string) => boolean; data: (k: string) => string }; renderedPosition: { x: number; y: number } }) => {
      if (evt.target.hasClass("has-modifiers")) {
        const label = evt.target.data("label") as string;
        const match = label.match(/\[mod: (\d+)\]/);
        const count = match ? parseInt(match[1], 10) : 0;
        if (count > 0) {
          setTooltip({
            x: evt.renderedPosition.x,
            y: evt.renderedPosition.y,
            content: { kind: "modifier-badge", count },
          });
        }
      }
    };

    const hideTooltip = () => setTooltip(null);

    cy.on("mouseover", "edge[edgeType = 'PREEMPTED_BY'], edge[edgeType = 'MODIFIES']", showEdgeTooltip);
    cy.on("mouseout", "edge", hideTooltip);
    cy.on("mouseover", "node.has-modifiers", showNodeTooltip);
    cy.on("mouseout", "node", hideTooltip);

    return () => {
      cy.off("mouseover", "edge[edgeType = 'PREEMPTED_BY'], edge[edgeType = 'MODIFIES']", showEdgeTooltip);
      cy.off("mouseout", "edge", hideTooltip);
      cy.off("mouseover", "node.has-modifiers", showNodeTooltip);
      cy.off("mouseout", "node", hideTooltip);
    };
  }, [cyRef, cyVersion]);

  if (!tooltip) return null;

  return (
    <div
      ref={containerRef}
      className="absolute pointer-events-none z-50"
      style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
      data-testid="graph-tooltip"
    >
      <div className="bg-white border border-slate-200 rounded shadow-lg px-3 py-2 max-w-xs text-xs">
        {tooltip.content.kind === "preemption" && (
          <>
            <div className="font-semibold text-red-700 mb-1">Preemption</div>
            <div><span className="text-slate-500">Priority:</span> {tooltip.content.edgePriority}</div>
            <div><span className="text-slate-500">Reason:</span> {tooltip.content.reason}</div>
          </>
        )}
        {tooltip.content.kind === "modifier" && (
          <>
            <div className="font-semibold text-orange-700 mb-1">Modifier</div>
            <div><span className="text-slate-500">Nature:</span> {tooltip.content.nature}</div>
            <div><span className="text-slate-500">Note:</span> {tooltip.content.note}</div>
            <div><span className="text-slate-500">Source:</span> {tooltip.content.sourceGuideline}</div>
          </>
        )}
        {tooltip.content.kind === "modifier-badge" && (
          <div className="text-orange-700">
            {tooltip.content.count} active modifier{tooltip.content.count > 1 ? "s" : ""}
          </div>
        )}
      </div>
    </div>
  );
}
