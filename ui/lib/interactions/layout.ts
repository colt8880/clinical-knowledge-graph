/**
 * Cytoscape layout config for the interactions view.
 *
 * Three fixed guideline clusters arranged in a triangle:
 *   USPSTF top, ACC/AHA bottom-right, KDIGO bottom-left.
 * Cross-edges render between cluster children.
 *
 * Uses cose-bilkent (already installed) with compound-node support
 * and fixed compound positions for layout stability.
 */

export const INTERACTIONS_LAYOUT_OPTIONS: { name: string; [key: string]: unknown } = {
  name: "cose-bilkent",
  quality: "default",
  nodeDimensionsIncludeLabels: true,
  idealEdgeLength: 150,
  nodeRepulsion: 6000,
  gravity: 0.3,
  gravityRange: 3.8,
  numIter: 2500,
  tile: true,
  tilingPaddingVertical: 20,
  tilingPaddingHorizontal: 20,
  animate: false,
  fit: true,
  padding: 50,
  // Seed for determinism.
  randomize: false,
};
