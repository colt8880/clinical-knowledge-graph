"use client";

import { useCallback, useRef } from "react";
import type { DomainKey } from "@/lib/explore/urlState";

interface DomainFilterProps {
  visibleDomains: DomainKey[];
  onChange: (domains: DomainKey[]) => void;
}

const DOMAINS: { key: DomainKey; label: string; color: string; activeClass: string }[] = [
  {
    key: "uspstf",
    label: "USPSTF",
    color: "border-blue-400",
    activeClass: "bg-blue-100 text-blue-800 border-blue-400",
  },
  {
    key: "acc-aha",
    label: "ACC/AHA",
    color: "border-purple-400",
    activeClass: "bg-purple-100 text-purple-800 border-purple-400",
  },
  {
    key: "kdigo",
    label: "KDIGO",
    color: "border-emerald-400",
    activeClass: "bg-emerald-100 text-emerald-800 border-emerald-400",
  },
  {
    key: "ada",
    label: "ADA",
    color: "border-amber-400",
    activeClass: "bg-amber-100 text-amber-800 border-amber-400",
  },
];

export default function DomainFilter({ visibleDomains, onChange }: DomainFilterProps) {
  const chipRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const toggle = useCallback(
    (key: DomainKey) => {
      if (visibleDomains.includes(key)) {
        onChange(visibleDomains.filter((d) => d !== key));
      } else {
        onChange([...visibleDomains, key]);
      }
    },
    [visibleDomains, onChange],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        const next = (index + 1) % DOMAINS.length;
        chipRefs.current[next]?.focus();
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        const prev = (index - 1 + DOMAINS.length) % DOMAINS.length;
        chipRefs.current[prev]?.focus();
      }
    },
    [],
  );

  return (
    <div
      role="group"
      aria-label="Guideline domain filter"
      className="flex flex-col gap-2 p-3"
      data-testid="domain-filter"
    >
      <span className="text-[11px] uppercase tracking-wide font-semibold text-slate-500">
        Guidelines
      </span>
      <div className="flex flex-wrap gap-2">
        {DOMAINS.map((d, i) => {
          const active = visibleDomains.includes(d.key);
          return (
            <button
              key={d.key}
              ref={(el) => { chipRefs.current[i] = el; }}
              role="checkbox"
              aria-checked={active}
              onClick={() => toggle(d.key)}
              onKeyDown={(e) => handleKeyDown(e, i)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border-2 transition-colors cursor-pointer select-none ${
                active
                  ? d.activeClass
                  : `bg-slate-50 text-slate-400 ${d.color} opacity-50`
              }`}
              data-testid={`domain-chip-${d.key}`}
            >
              {d.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
