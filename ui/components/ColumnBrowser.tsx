/**
 * Shared graph-hierarchy utilities used by the Explore page.
 */

import type { GraphNode } from "@/lib/api/client";

/** Hierarchy rank — lower number = higher in the tree. */
export const TYPE_RANK: Record<string, number> = {
  Guideline: 0,
  Recommendation: 1,
  Strategy: 2,
  Condition: 3,
  Medication: 3,
  Procedure: 3,
  Observation: 3,
};

/**
 * Given a subgraph's node list and a center node id, return only
 * the nodes that are children (lower in the hierarchy) of the center.
 */
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
