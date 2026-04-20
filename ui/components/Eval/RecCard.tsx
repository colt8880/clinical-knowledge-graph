"use client";

import { useState, useCallback } from "react";
import type { RecCardData, ConvergenceEntry } from "@/lib/recListBuilder";

// Domain badge colors — matches F28 palette.
const DOMAIN_BADGE: Record<string, { bg: string; text: string; dot: string }> = {
  USPSTF: { bg: "bg-blue-100", text: "text-blue-800", dot: "bg-blue-600" },
  ACC_AHA: { bg: "bg-purple-100", text: "text-purple-800", dot: "bg-purple-600" },
  KDIGO: { bg: "bg-emerald-100", text: "text-emerald-800", dot: "bg-emerald-600" },
};

const DEFAULT_BADGE = { bg: "bg-slate-100", text: "text-slate-700", dot: "bg-slate-500" };

// Status styling.
const STATUS_STYLE: Record<string, { border: string; bg: string; text: string; badge: string }> = {
  due: {
    border: "border-blue-300",
    bg: "bg-blue-50",
    text: "text-blue-800",
    badge: "bg-blue-600 text-white",
  },
  up_to_date: {
    border: "border-green-300",
    bg: "bg-green-50",
    text: "text-green-800",
    badge: "bg-green-600 text-white",
  },
  not_applicable: {
    border: "border-slate-200",
    bg: "bg-slate-50",
    text: "text-slate-600",
    badge: "bg-slate-400 text-white",
  },
  insufficient_evidence: {
    border: "border-slate-200",
    bg: "bg-slate-50",
    text: "text-slate-600",
    badge: "bg-slate-400 text-white",
  },
};

/** Format evidence grade for display. ACC/AHA uses "COR I / LOE A" format. */
function formatGrade(grade: string, domain: string): string {
  if (domain === "ACC_AHA" && grade.startsWith("COR")) return grade;
  if (domain === "KDIGO" && /^\d/.test(grade)) return grade;
  return `Grade ${grade}`;
}

/** Format domain key for display. */
function formatDomainLabel(domain: string): string {
  if (domain === "ACC_AHA") return "ACC/AHA";
  return domain;
}

interface RecCardProps {
  card: RecCardData;
  isHighlighted: boolean;
  onConvergenceClick: (relatedRecIds: string[]) => void;
}

export default function RecCard({ card, isHighlighted, onConvergenceClick }: RecCardProps) {
  const [expanded, setExpanded] = useState(false);

  const domainStyle = DOMAIN_BADGE[card.domain] ?? DEFAULT_BADGE;
  const statusStyle = STATUS_STYLE[card.status] ?? STATUS_STYLE.not_applicable;

  const handleConvergenceClick = useCallback(() => {
    // Collect all rec IDs from convergence entries (excluding this card)
    const relatedIds = new Set<string>();
    for (const entry of card.convergence) {
      for (const r of entry.recommended_by) {
        if (r.rec_id !== card.recommendation_id) {
          relatedIds.add(r.rec_id);
        }
      }
    }
    onConvergenceClick(Array.from(relatedIds));
  }, [card, onConvergenceClick]);

  const highlightRing = isHighlighted ? "ring-2 ring-amber-400" : "";

  return (
    <div
      className={`rounded border ${statusStyle.border} ${statusStyle.bg} px-4 py-3 transition-shadow ${highlightRing}`}
      data-testid="rec-card"
      data-rec-id={card.recommendation_id}
    >
      {/* Header: domain badge + grade pill + status badge + rec id */}
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-semibold rounded ${domainStyle.bg} ${domainStyle.text}`}
          data-testid="domain-badge"
        >
          <span className={`w-2 h-2 rounded-full ${domainStyle.dot}`} />
          {formatDomainLabel(card.domain)}
        </span>
        <span
          className="inline-block px-2 py-0.5 text-[11px] font-bold rounded bg-slate-700 text-white"
          data-testid="grade-pill"
        >
          {formatGrade(card.evidence_grade, card.domain)}
        </span>
        <span
          className={`inline-block px-2 py-0.5 text-[11px] font-semibold uppercase rounded ${statusStyle.badge}`}
        >
          {card.status.replace(/_/g, " ")}
        </span>
        <span className="text-xs text-slate-500 font-mono">
          {card.recommendation_id}
        </span>
      </div>

      {/* Action summary */}
      {card.action_summary && (
        <p className={`text-sm font-medium mb-1 ${statusStyle.text}`}>
          {card.action_summary}
        </p>
      )}

      {/* Reason */}
      <p className={`text-sm leading-relaxed ${statusStyle.text}`}>
        {card.reason}
      </p>

      {/* Convergence indicator */}
      {card.convergence.length > 0 && (
        <button
          className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-amber-50 border border-amber-200 text-amber-800 hover:bg-amber-100 transition-colors cursor-pointer"
          onClick={handleConvergenceClick}
          data-testid="convergence-badge"
          title="Click to highlight related recommendations"
        >
          <ConvergenceIcon />
          Also recommended by:{" "}
          {uniqueOtherGuidelines(card).map((g, i) => (
            <span key={g.domain} className="inline-flex items-center gap-0.5">
              {i > 0 && ", "}
              <span
                className={`w-1.5 h-1.5 rounded-full ${(DOMAIN_BADGE[g.domain] ?? DEFAULT_BADGE).dot}`}
              />
              {g.label}
            </span>
          ))}
        </button>
      )}

      {/* Expandable strategy fan-out */}
      {card.actions.length > 0 && (
        <div className="mt-2">
          <button
            className="text-xs text-slate-500 hover:text-slate-700 underline"
            onClick={() => setExpanded(!expanded)}
            data-testid="expand-actions"
          >
            {expanded ? "Hide actions" : `Show ${card.actions.length} actions`}
          </button>
          {expanded && (
            <ul className="mt-1 space-y-0.5" data-testid="action-list">
              {card.actions.map((a) => (
                <li
                  key={a.action_node_id}
                  className="text-xs text-slate-600 flex items-center gap-1.5"
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${a.satisfied ? "bg-green-500" : "bg-slate-300"}`}
                  />
                  <span className="font-mono">{a.action_node_id}</span>
                  <span className="text-slate-400">({a.entity_type})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Offered strategies (when status is due) */}
      {card.offered_strategies && card.offered_strategies.length > 0 && !expanded && (
        <div className="mt-1.5 text-xs text-slate-500">
          Offered strategies: {card.offered_strategies.join(", ")}
        </div>
      )}
    </div>
  );
}

function ConvergenceIcon() {
  return (
    <svg
      className="w-3 h-3 text-amber-600"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
      />
    </svg>
  );
}

/** Get unique guidelines from convergence entries, excluding this card's guideline. */
function uniqueOtherGuidelines(card: RecCardData): { domain: string; label: string }[] {
  const seen = new Set<string>();
  const result: { domain: string; label: string }[] = [];
  for (const entry of card.convergence) {
    for (const r of entry.recommended_by) {
      if (r.domain !== card.domain && !seen.has(r.domain)) {
        seen.add(r.domain);
        result.push({ domain: r.domain, label: r.guideline });
      }
    }
  }
  return result;
}
