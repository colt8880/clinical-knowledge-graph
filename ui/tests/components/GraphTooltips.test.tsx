import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, act } from "@testing-library/react";
import GraphTooltips from "@/components/GraphTooltips";
import type { Core } from "cytoscape";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function createMockCy() {
  const handlers: Record<string, ((...args: unknown[]) => void)[]> = {};

  const mockCy = {
    on: vi.fn((event: string, _selector: string, handler: (...args: unknown[]) => void) => {
      if (!handlers[event]) handlers[event] = [];
      handlers[event].push(handler);
    }),
    off: vi.fn(),
    // Simulate firing an event.
    _fire: (event: string, data: unknown) => {
      for (const h of handlers[event] ?? []) {
        h(data);
      }
    },
  } as unknown as Core;

  return { mockCy, handlers };
}

describe("GraphTooltips", () => {
  it("renders nothing when no tooltip is active", () => {
    const { mockCy } = createMockCy();
    const cyRef = { current: mockCy };

    const { container } = render(
      <GraphTooltips cyRef={cyRef} cyVersion={1} />,
    );
    expect(screen.queryByTestId("graph-tooltip")).toBeNull();
    expect(container.innerHTML).toBe("");
  });

  it("shows preemption tooltip on mouseover of PREEMPTED_BY edge", () => {
    const { mockCy } = createMockCy();
    const cyRef = { current: mockCy };

    render(<GraphTooltips cyRef={cyRef} cyVersion={1} />);

    // Simulate mouseover event on a PREEMPTED_BY edge.
    const onCall = (mockCy.on as ReturnType<typeof vi.fn>).mock.calls.find(
      (c: unknown[]) => c[0] === "mouseover" && typeof c[1] === "string" && c[1].includes("PREEMPTED_BY"),
    );
    expect(onCall).toBeDefined();

    const handler = onCall![2] as (evt: unknown) => void;
    act(() => {
      handler({
        target: {
          data: (k: string) => {
            if (k === "edgeType") return "PREEMPTED_BY";
            if (k === "edgePriority") return "200";
            if (k === "edgeReason") return "ACC/AHA takes precedence";
            return undefined;
          },
        },
        renderedPosition: { x: 100, y: 200 },
      });
    });

    const tooltip = screen.getByTestId("graph-tooltip");
    expect(tooltip).toBeDefined();
    expect(tooltip.textContent).toContain("Preemption");
    expect(tooltip.textContent).toContain("200");
  });

  it("shows modifier tooltip on mouseover of MODIFIES edge", () => {
    const { mockCy } = createMockCy();
    const cyRef = { current: mockCy };

    render(<GraphTooltips cyRef={cyRef} cyVersion={1} />);

    const onCall = (mockCy.on as ReturnType<typeof vi.fn>).mock.calls.find(
      (c: unknown[]) => c[0] === "mouseover" && typeof c[1] === "string" && c[1].includes("MODIFIES"),
    );
    expect(onCall).toBeDefined();

    const handler = onCall![2] as (evt: unknown) => void;
    act(() => {
      handler({
        target: {
          data: (k: string) => {
            if (k === "edgeType") return "MODIFIES";
            if (k === "edgeNature") return "intensity_reduction";
            if (k === "edgeNote") return "KDIGO modifies intensity";
            if (k === "edgeSourceGuideline") return "guideline:kdigo-ckd-2024";
            return undefined;
          },
        },
        renderedPosition: { x: 150, y: 250 },
      });
    });

    const tooltip = screen.getByTestId("graph-tooltip");
    expect(tooltip).toBeDefined();
    expect(tooltip.textContent).toContain("Modifier");
    expect(tooltip.textContent).toContain("intensity_reduction");
  });

  it("hides tooltip on mouseout", () => {
    const { mockCy } = createMockCy();
    const cyRef = { current: mockCy };

    render(<GraphTooltips cyRef={cyRef} cyVersion={1} />);

    // Show a tooltip first.
    const showCall = (mockCy.on as ReturnType<typeof vi.fn>).mock.calls.find(
      (c: unknown[]) => c[0] === "mouseover" && typeof c[1] === "string" && c[1].includes("PREEMPTED_BY"),
    );
    const showHandler = showCall![2] as (evt: unknown) => void;
    act(() => {
      showHandler({
        target: {
          data: (k: string) => (k === "edgeType" ? "PREEMPTED_BY" : "—"),
        },
        renderedPosition: { x: 100, y: 200 },
      });
    });
    expect(screen.getByTestId("graph-tooltip")).toBeDefined();

    // Now trigger mouseout.
    const hideCall = (mockCy.on as ReturnType<typeof vi.fn>).mock.calls.find(
      (c: unknown[]) => c[0] === "mouseout" && c[1] === "edge",
    );
    expect(hideCall).toBeDefined();
    const hideHandler = hideCall![2] as () => void;
    act(() => {
      hideHandler();
    });

    expect(screen.queryByTestId("graph-tooltip")).toBeNull();
  });
});
