import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import TraceStepper from "@/components/TraceStepper";

afterEach(() => {
  cleanup();
});

describe("TraceStepper", () => {
  const defaultProps = {
    currentIndex: 0,
    totalEvents: 10,
    onPrev: vi.fn(),
    onNext: vi.fn(),
    onJump: vi.fn(),
  };

  it("renders stepper controls", () => {
    render(<TraceStepper {...defaultProps} />);
    expect(screen.getByTestId("trace-stepper")).toBeDefined();
    expect(screen.getByText("Prev")).toBeDefined();
    expect(screen.getByText("Next")).toBeDefined();
  });

  it("disables Prev on first event", () => {
    render(<TraceStepper {...defaultProps} currentIndex={0} />);
    const prev = screen.getByText("Prev") as HTMLButtonElement;
    expect(prev.disabled).toBe(true);
  });

  it("disables Next on last event", () => {
    render(<TraceStepper {...defaultProps} currentIndex={9} />);
    const next = screen.getByText("Next") as HTMLButtonElement;
    expect(next.disabled).toBe(true);
  });

  it("shows preemption icon when currentEventType is preemption_resolved", () => {
    render(
      <TraceStepper
        {...defaultProps}
        currentEventType="preemption_resolved"
      />,
    );
    const icon = screen.getByTestId("icon-preemption");
    expect(icon).toBeDefined();
    expect(icon.textContent).toContain("Preempted");
  });

  it("shows modifier icon when currentEventType is cross_guideline_match", () => {
    render(
      <TraceStepper
        {...defaultProps}
        currentEventType="cross_guideline_match"
      />,
    );
    const icon = screen.getByTestId("icon-modifier");
    expect(icon).toBeDefined();
    expect(icon.textContent).toContain("Modifier");
  });

  it("shows no icon for regular event types", () => {
    render(
      <TraceStepper
        {...defaultProps}
        currentEventType="recommendation_considered"
      />,
    );
    expect(screen.queryByTestId("icon-preemption")).toBeNull();
    expect(screen.queryByTestId("icon-modifier")).toBeNull();
  });

  it("returns null when totalEvents is 0", () => {
    const { container } = render(
      <TraceStepper {...defaultProps} totalEvents={0} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("calls onNext when Next is clicked", () => {
    const onNext = vi.fn();
    render(<TraceStepper {...defaultProps} currentIndex={3} onNext={onNext} />);
    fireEvent.click(screen.getByText("Next"));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it("calls onPrev when Prev is clicked", () => {
    const onPrev = vi.fn();
    render(<TraceStepper {...defaultProps} currentIndex={3} onPrev={onPrev} />);
    fireEvent.click(screen.getByText("Prev"));
    expect(onPrev).toHaveBeenCalledTimes(1);
  });
});
