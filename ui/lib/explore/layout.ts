/**
 * Cytoscape layout configuration for whole-forest mode.
 *
 * Uses cose-bilkent with compound nodes (one per guideline domain).
 * Shared entities sit outside compound nodes in a central zone.
 *
 * Choice rationale: cose-bilkent handles compound nodes well, produces
 * readable tree-ish clusters per guideline, and positions shared entities
 * centrally where multiple guidelines connect to them. Preferred over
 * dagre-per-cluster (too rigid with shared entities) and plain fcose
 * (less structured). Already installed as a dependency.
 */

import type { LayoutOptions } from "cytoscape";

/**
 * Compound-node parent IDs for each domain cluster.
 * Used as parent references in Cytoscape element data.
 */
export const DOMAIN_PARENTS: Record<string, string> = {
  USPSTF: "__cluster_uspstf",
  ACC_AHA: "__cluster_acc_aha",
  KDIGO: "__cluster_kdigo",
};

/** Layout options for the whole-forest view. */
export const FOREST_LAYOUT_OPTIONS: LayoutOptions = {
  name: "cose-bilkent",
  // @ts-expect-error — cose-bilkent options not in base LayoutOptions
  quality: "default",
  nodeDimensionsIncludeLabels: true,
  idealEdgeLength: 120,
  nodeRepulsion: 8000,
  gravity: 0.25,
  gravityRange: 3.8,
  numIter: 2500,
  tile: true,
  tilingPaddingVertical: 30,
  tilingPaddingHorizontal: 30,
  animate: false,
  fit: true,
  padding: 40,
};
