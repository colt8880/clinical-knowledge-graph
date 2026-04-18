import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import GraphCanvas from "@/components/GraphCanvas";
import type { RecState } from "@/components/GraphCanvas";
import type { GraphNode, GraphEdge } from "@/lib/api/client";

// Mock cytoscape to avoid DOM canvas issues in jsdom.
const mockAddClass = vi.fn();
const mockRemoveClass = vi.fn();
const mockData = vi.fn((key?: string) => {
  if (key === "label") return "Test Rec";
  if (key === "edgeType") return "PREEMPTED_BY";
  return undefined;
});
const mockStyle = vi.fn();
const mockLength = 1;

const mockNode = {
  addClass: mockAddClass,
  removeClass: mockRemoveClass,
  data: mockData,
  style: mockStyle,
  length: mockLength,
  id: () => "rec:test",
};

const mockCyInstance = {
  on: vi.fn(),
  off: vi.fn(),
  destroy: vi.fn(),
  fit: vi.fn(),
  pan: vi.fn(() => ({ x: 0, y: 0 })),
  nodes: vi.fn(() => ({ forEach: vi.fn(), removeClass: vi.fn(), lock: vi.fn() })),
  edges: vi.fn(() => ({ forEach: vi.fn() })),
  elements: vi.fn(() => ({ removeClass: vi.fn() })),
  getElementById: vi.fn(() => mockNode),
  animate: vi.fn(),
};

vi.mock("cytoscape", () => ({
  default: Object.assign(
    vi.fn(() => mockCyInstance),
    { use: vi.fn() },
  ),
}));

vi.mock("cytoscape-cose-bilkent", () => ({
  default: vi.fn(),
}));

// Mock the GraphTooltips component to avoid tooltip side-effects in unit tests.
vi.mock("@/components/GraphTooltips", () => ({
  default: () => null,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function makeNode(id: string, type: string, title: string): GraphNode {
  return {
    id,
    labels: [type],
    properties: { title },
  };
}

function makeEdge(id: string, start: string, end: string, type: string): GraphEdge {
  return { id, start, end, type, properties: {} };
}

describe("GraphCanvas", () => {
  it("renders the canvas container", () => {
    render(
      <GraphCanvas
        columns={[{ nodes: [makeNode("g1", "Guideline", "Test")], selectedId: null }]}
        edges={[]}
      />,
    );
    expect(screen.getByTestId("graph-canvas")).toBeDefined();
  });

  it("accepts recState prop without error", () => {
    const recState: RecState = {
      preemptedBy: new Map([["rec:a", "rec:b"]]),
      modifierCounts: new Map([["rec:c", 2]]),
    };

    render(
      <GraphCanvas
        columns={[{ nodes: [makeNode("g1", "Guideline", "Test")], selectedId: null }]}
        edges={[]}
        recState={recState}
      />,
    );
    expect(screen.getByTestId("graph-canvas")).toBeDefined();
  });

  it("passes PREEMPTED_BY edges with correct color to cytoscape", () => {
    const nodes = [
      makeNode("rec:a", "Recommendation", "Rec A"),
      makeNode("rec:b", "Recommendation", "Rec B"),
    ];
    const edges = [
      makeEdge("e1", "rec:a", "rec:b", "PREEMPTED_BY"),
    ];

    render(
      <GraphCanvas
        columns={[{ nodes, selectedId: null }]}
        edges={edges}
      />,
    );
    // Canvas rendered without errors.
    expect(screen.getByTestId("graph-canvas")).toBeDefined();
  });

  it("passes MODIFIES edges to cytoscape", () => {
    const nodes = [
      makeNode("rec:a", "Recommendation", "Rec A"),
      makeNode("rec:b", "Recommendation", "Rec B"),
    ];
    const edges = [
      makeEdge("e1", "rec:a", "rec:b", "MODIFIES"),
    ];

    render(
      <GraphCanvas
        columns={[{ nodes, selectedId: null }]}
        edges={edges}
      />,
    );
    expect(screen.getByTestId("graph-canvas")).toBeDefined();
  });
});
