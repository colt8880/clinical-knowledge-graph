/**
 * Scoped subgraph extraction for per-guideline detail view.
 *
 * Given the full forest subgraph and a target guideline slug,
 * returns only that guideline's nodes plus the shared clinical
 * entities reachable from its strategy nodes. Cross-guideline
 * edges (PREEMPTED_BY, MODIFIES) are excluded.
 */

import type { ForestNode, GraphEdge, ForestSubgraph } from "@/lib/api/client";

/** Map from URL slug to Neo4j domain label. */
const SLUG_TO_DOMAIN: Record<string, string> = {
  "uspstf-statin-2022": "USPSTF",
  "acc-aha-cholesterol-2018": "ACC_AHA",
  "kdigo-ckd-2024": "KDIGO",
};

/** Edge types that cross guideline boundaries and should be excluded. */
const CROSS_GUIDELINE_EDGE_TYPES = new Set(["PREEMPTED_BY", "MODIFIES"]);

export interface ScopedSubgraph {
  nodes: ForestNode[];
  edges: GraphEdge[];
  /** Node IDs that have cross-guideline edges (for badge rendering). */
  crossGuidelineNodeIds: Set<string>;
}

/**
 * Extract the scoped subgraph for a single guideline.
 *
 * Included nodes:
 * - All nodes with the target domain label (Guideline, Rec, Strategy)
 * - All shared entities (domain === null) reachable via edges from
 *   the target guideline's nodes
 *
 * Excluded edges:
 * - PREEMPTED_BY and MODIFIES (cross-guideline)
 * - Any edge where one endpoint is outside the scoped node set
 */
export function extractScopedSubgraph(
  forest: ForestSubgraph,
  guidelineSlug: string,
): ScopedSubgraph {
  const targetDomain = SLUG_TO_DOMAIN[guidelineSlug];
  if (!targetDomain) {
    return { nodes: [], edges: [], crossGuidelineNodeIds: new Set() };
  }

  // Build node lookup by ID for O(1) access.
  const nodeById = new Map<string, ForestNode>();
  for (const node of forest.nodes) {
    nodeById.set(node.id, node);
  }

  // Step 1: collect guideline-scoped nodes.
  const guidelineNodeIds = new Set<string>();
  for (const node of forest.nodes) {
    if (node.domain === targetDomain) {
      guidelineNodeIds.add(node.id);
    }
  }

  // Step 2: find shared entities reachable from guideline-scoped nodes.
  const sharedEntityIds = new Set<string>();
  for (const edge of forest.edges) {
    if (CROSS_GUIDELINE_EDGE_TYPES.has(edge.type)) continue;

    if (guidelineNodeIds.has(edge.start)) {
      const targetNode = nodeById.get(edge.end);
      if (targetNode && targetNode.domain === null) {
        sharedEntityIds.add(edge.end);
      }
    }
    if (guidelineNodeIds.has(edge.end)) {
      const sourceNode = nodeById.get(edge.start);
      if (sourceNode && sourceNode.domain === null) {
        sharedEntityIds.add(edge.start);
      }
    }
  }

  const scopedNodeIds = new Set<string>();
  guidelineNodeIds.forEach((id) => scopedNodeIds.add(id));
  sharedEntityIds.forEach((id) => scopedNodeIds.add(id));

  // Step 3: collect nodes.
  const nodes = forest.nodes.filter((n) => scopedNodeIds.has(n.id));

  // Step 4: identify cross-guideline node IDs (nodes with PREEMPTED_BY
  // or MODIFIES edges where the other endpoint is outside scope).
  const crossGuidelineNodeIds = new Set<string>();
  for (const edge of forest.edges) {
    if (!CROSS_GUIDELINE_EDGE_TYPES.has(edge.type)) continue;
    if (scopedNodeIds.has(edge.start) && !scopedNodeIds.has(edge.end)) {
      crossGuidelineNodeIds.add(edge.start);
    }
    if (scopedNodeIds.has(edge.end) && !scopedNodeIds.has(edge.start)) {
      crossGuidelineNodeIds.add(edge.end);
    }
  }

  // Step 5: filter edges — both endpoints in scope, no cross-guideline types.
  const edges = forest.edges.filter(
    (e) =>
      scopedNodeIds.has(e.start) &&
      scopedNodeIds.has(e.end) &&
      !CROSS_GUIDELINE_EDGE_TYPES.has(e.type),
  );

  return { nodes, edges, crossGuidelineNodeIds };
}
