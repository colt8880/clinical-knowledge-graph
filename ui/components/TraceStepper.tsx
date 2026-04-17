"use client";

import { useEffect, useCallback } from "react";

interface TraceStepperProps {
  currentIndex: number;
  totalEvents: number;
  currentEventType?: string | null;
  onPrev: () => void;
  onNext: () => void;
  onJump: (index: number) => void;
  onNavigateToEvent?: (eventType: string) => void;
}

/** Event type icon for cross-guideline events. */
function EventTypeIcon({ type }: { type: string | null | undefined }) {
  if (type === "preemption_resolved") {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-700"
        title="Preemption resolved"
        data-testid="icon-preemption"
      >
        <span className="line-through">Rec</span> Preempted
      </span>
    );
  }
  if (type === "cross_guideline_match") {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-orange-100 text-orange-700"
        title="Cross-guideline modifier"
        data-testid="icon-modifier"
      >
        &#8646; Modifier
      </span>
    );
  }
  return null;
}

export default function TraceStepper({
  currentIndex,
  totalEvents,
  currentEventType,
  onPrev,
  onNext,
  onJump,
}: TraceStepperProps) {
  // Keyboard shortcuts: arrow left/right for prev/next.
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input.
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      )
        return;

      if (e.key === "ArrowLeft" || e.key === "k") {
        e.preventDefault();
        onPrev();
      } else if (e.key === "ArrowRight" || e.key === "j") {
        e.preventDefault();
        onNext();
      }
    },
    [onPrev, onNext],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (totalEvents === 0) return null;

  return (
    <div
      className="flex items-center gap-3 px-3 py-2 bg-slate-50 border-b border-slate-200"
      data-testid="trace-stepper"
    >
      <button
        className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300 disabled:opacity-40"
        onClick={onPrev}
        disabled={currentIndex === 0}
        aria-label="Previous event"
      >
        Prev
      </button>
      <span className="text-xs text-slate-600 font-mono">
        {currentIndex + 1} / {totalEvents}
      </span>
      <button
        className="px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300 disabled:opacity-40"
        onClick={onNext}
        disabled={currentIndex >= totalEvents - 1}
        aria-label="Next event"
      >
        Next
      </button>
      <input
        type="number"
        className="w-14 text-xs border border-slate-300 rounded px-1.5 py-1 text-center"
        min={1}
        max={totalEvents}
        value={currentIndex + 1}
        onChange={(e) => {
          const val = parseInt(e.target.value, 10);
          if (!isNaN(val) && val >= 1 && val <= totalEvents) {
            onJump(val - 1);
          }
        }}
        aria-label="Jump to step"
      />
      <EventTypeIcon type={currentEventType} />
      <span className="text-[10px] text-slate-400 ml-auto">
        Use arrow keys to step
      </span>
    </div>
  );
}
