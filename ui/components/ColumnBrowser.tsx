"use client";

import type { GraphNode } from "@/lib/api/client";

/** Hierarchy rank — lower number = higher in the tree. */
const TYPE_RANK: Record<string, number> = {
  Guideline: 0,
  Recommendation: 1,
  Strategy: 2,
  Condition: 3,
  Medication: 3,
  Procedure: 3,
  Observation: 3,
};

const TYPE_COLORS: Record<string, string> = {
  Guideline: "#6b21a8",
  Recommendation: "#1e40af",
  Strategy: "#92400e",
  Condition: "#991b1b",
  Procedure: "#166534",
  Observation: "#3730a3",
  Medication: "#9d174d",
};

const COLUMN_LABELS: Record<string, string> = {
  Guideline: "Guidelines",
  Recommendation: "Recommendations",
  Strategy: "Strategies",
  Medication: "Actions",
  Procedure: "Actions",
  Observation: "Actions",
};

export interface Column {
  /** Label for the column header. */
  label: string;
  /** Nodes displayed in this column. */
  nodes: GraphNode[];
  /** Which node in this column is selected (drives the next column). */
  selectedId: string | null;
}

function nodeDisplayName(node: GraphNode): string {
  return (
    (node.properties.title as string) ??
    (node.properties.name as string) ??
    (node.properties.display_name as string) ??
    node.id
  );
}

function nodeBadge(node: GraphNode): string | null {
  const grade = node.properties.evidence_grade as string | undefined;
  if (grade) return `Grade ${grade}`;
  return null;
}

const GRADE_COLORS: Record<string, string> = {
  B: "bg-green-100 text-green-800",
  C: "bg-amber-100 text-amber-800",
  I: "bg-slate-100 text-slate-600",
};

interface ColumnBrowserProps {
  columns: Column[];
  onSelect: (columnIndex: number, nodeId: string) => void;
  onNodeDetail: (nodeId: string) => void;
  detailNodeId: string | null;
}

export function getColumnLabel(nodes: GraphNode[]): string {
  if (nodes.length === 0) return "Nodes";
  const type = nodes[0].labels[0];
  return COLUMN_LABELS[type] ?? `${type}s`;
}

export function filterChildren(
  allNodes: GraphNode[],
  centerId: string,
): GraphNode[] {
  const center = allNodes.find((n) => n.id === centerId);
  if (!center) return [];
  const centerRank = TYPE_RANK[center.labels[0]] ?? 99;
  return allNodes.filter((n) => {
    if (n.id === centerId) return false;
    const rank = TYPE_RANK[n.labels[0]] ?? 99;
    return rank > centerRank;
  });
}

export default function ColumnBrowser({
  columns,
  onSelect,
  onNodeDetail,
  detailNodeId,
}: ColumnBrowserProps) {
  return (
    <div className="flex h-full overflow-x-auto" data-testid="column-browser">
      {columns.map((col, colIdx) => (
        <div
          key={colIdx}
          className="flex flex-col min-w-[220px] max-w-[280px] w-[240px] border-r border-slate-200 bg-white shrink-0"
        >
          <div className="px-3 pt-3 pb-2 border-b border-slate-100">
            <h2 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500">
              {col.label}
            </h2>
          </div>
          <ul className="flex-1 overflow-y-auto py-1 px-1.5">
            {col.nodes.map((node) => {
              const isSelected = node.id === col.selectedId;
              const isDetail = node.id === detailNodeId;
              const badge = nodeBadge(node);
              const dotColor = TYPE_COLORS[node.labels[0]] ?? "#64748b";

              return (
                <li key={node.id}>
                  <button
                    onClick={() => onSelect(colIdx, node.id)}
                    onDoubleClick={() => onNodeDetail(node.id)}
                    className={`w-full text-left px-2.5 py-2 rounded-md text-xs transition-colors mb-0.5 ${
                      isSelected
                        ? "bg-blue-50 text-blue-900 font-medium ring-1 ring-blue-200"
                        : isDetail
                          ? "bg-slate-100 text-slate-900"
                          : "text-slate-700 hover:bg-slate-50"
                    }`}
                    title={node.id}
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className="inline-block w-2 h-2 rounded-full mt-1 shrink-0"
                        style={{ backgroundColor: dotColor }}
                      />
                      <div className="min-w-0">
                        <div className="leading-snug">
                          {nodeDisplayName(node)}
                        </div>
                        {badge && (
                          <span
                            className={`inline-block mt-1 px-1.5 py-0 text-[10px] font-semibold rounded ${
                              GRADE_COLORS[
                                node.properties.evidence_grade as string
                              ] ?? "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {badge}
                          </span>
                        )}
                      </div>
                      {isSelected && (
                        <svg
                          className="w-3 h-3 text-slate-400 mt-0.5 ml-auto shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      )}
                    </div>
                  </button>
                </li>
              );
            })}
            {col.nodes.length === 0 && (
              <li className="text-xs text-slate-400 italic px-2 py-4 text-center">
                No items
              </li>
            )}
          </ul>
        </div>
      ))}
    </div>
  );
}
