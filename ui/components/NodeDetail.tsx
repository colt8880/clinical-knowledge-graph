"use client";

import { useState } from "react";
import type { GraphNode, GraphEdge } from "@/lib/api/client";
import { predicateToNaturalLanguage } from "@/lib/predicates/naturalLanguage";

interface NodeDetailProps {
  node: (GraphNode & { domain?: string | null }) | null;
  edge: GraphEdge | null;
}

const SYSTEM_NAMES: Record<string, string> = {
  rxnorm: "RxNorm",
  snomed: "SNOMED CT",
  loinc: "LOINC",
  icd10: "ICD-10-CM",
  cpt: "CPT",
};

const TYPE_BADGE_COLORS: Record<string, string> = {
  Guideline: "bg-purple-100 text-purple-800 border-purple-300",
  Recommendation: "bg-blue-100 text-blue-800 border-blue-300",
  Strategy: "bg-amber-100 text-amber-800 border-amber-300",
  Condition: "bg-red-100 text-red-800 border-red-300",
  Procedure: "bg-green-100 text-green-800 border-green-300",
  Observation: "bg-indigo-100 text-indigo-800 border-indigo-300",
  Medication: "bg-pink-100 text-pink-800 border-pink-300",
};

const DOMAIN_BADGE_COLORS: Record<string, string> = {
  USPSTF: "bg-blue-100 text-blue-800 border-blue-300",
  ACC_AHA: "bg-purple-100 text-purple-800 border-purple-300",
  KDIGO: "bg-emerald-100 text-emerald-800 border-emerald-300",
};

const DOMAIN_DISPLAY: Record<string, string> = {
  USPSTF: "USPSTF",
  ACC_AHA: "ACC/AHA",
  KDIGO: "KDIGO",
};

/** Domain labels to filter out of generic badge list (shown via DomainBadge instead). */
const DOMAIN_LABELS = new Set(["USPSTF", "ACC_AHA", "KDIGO"]);

function Badge({ label }: { label: string }) {
  const colors =
    TYPE_BADGE_COLORS[label] ?? "bg-slate-100 text-slate-700 border-slate-300";
  return (
    <span
      className={`inline-block px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide rounded border ${colors}`}
    >
      {label}
    </span>
  );
}

function DomainBadge({ domain }: { domain: string }) {
  const colors = DOMAIN_BADGE_COLORS[domain] ?? "bg-slate-100 text-slate-700 border-slate-300";
  const display = DOMAIN_DISPLAY[domain] ?? domain;
  return (
    <span
      className={`inline-block px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide rounded border ${colors}`}
      data-testid="domain-badge"
    >
      {display}
    </span>
  );
}

// ── Structured eligibility renderer ────────────────────────────────

interface PredicateNode {
  predicate?: string;
  all_of?: PredicateNode[];
  any_of?: PredicateNode[];
  none_of?: PredicateNode[];
  [key: string]: unknown;
}

function formatPredicateArgs(node: PredicateNode): string {
  const skip = new Set(["predicate", "all_of", "any_of", "none_of"]);
  const args = Object.entries(node)
    .filter(([k]) => !skip.has(k))
    .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
    .join(", ");
  return args;
}

const COMPOSITE_OPS = new Set(["all_of", "any_of", "none_of"]);

const OP_STYLE: Record<string, { label: string; color: string }> = {
  all_of: { label: "ALL OF", color: "text-green-700" },
  any_of: { label: "ANY OF", color: "text-amber-700" },
  none_of: { label: "NONE OF", color: "text-red-700" },
};

function PredicateTree({ node, depth = 0 }: { node: PredicateNode; depth?: number }) {
  const entries = Object.entries(node);

  return (
    <>
      {entries.map(([key, value], i) => {
        // Composite operator — recurse into children.
        if (COMPOSITE_OPS.has(key) && Array.isArray(value)) {
          const { label, color } = OP_STYLE[key]!;
          return (
            <div key={i} className="py-0.5">
              <div
                className={`text-[11px] font-semibold uppercase tracking-wide ${color}`}
                style={{ paddingLeft: depth * 16 }}
              >
                {label}
              </div>
              {(value as PredicateNode[]).map((child, j) => (
                <PredicateTree key={j} node={child} depth={depth + 1} />
              ))}
            </div>
          );
        }

        // Explicit "predicate" field (spec format).
        if (key === "predicate") return null; // handled below

        // Leaf predicate — the key is the predicate name, value is its args.
        // e.g. {"age_between": {"min": 40, "max": 75}}
        if (typeof value === "object" && value !== null && !Array.isArray(value)) {
          const args = Object.entries(value as Record<string, unknown>)
            .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
            .join(", ");
          return (
            <div key={i} className="flex items-start gap-1.5 py-0.5" style={{ paddingLeft: depth * 16 }}>
              <span className="text-blue-700 font-mono text-xs font-medium">{key}</span>
              {args && <span className="text-slate-500 font-mono text-xs">({args})</span>}
            </div>
          );
        }

        return null;
      })}

      {/* Handle explicit "predicate" field format: {predicate: "name", arg1: val1} */}
      {node.predicate && (
        <div className="flex items-start gap-1.5 py-0.5" style={{ paddingLeft: depth * 16 }}>
          <span className="text-blue-700 font-mono text-xs font-medium">{node.predicate}</span>
          {formatPredicateArgs(node) && (
            <span className="text-slate-500 font-mono text-xs">({formatPredicateArgs(node)})</span>
          )}
        </div>
      )}
    </>
  );
}

function EligibilityBlock({ value }: { value: unknown }) {
  const [showJson, setShowJson] = useState(false);

  if (!value) return null;

  // Try parsing if it's a string (JSON stored as text in Neo4j).
  let parsed: PredicateNode;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value) as PredicateNode;
    } catch {
      return (
        <pre className="bg-white border border-slate-200 rounded p-2 text-xs font-mono overflow-x-auto">
          {value}
        </pre>
      );
    }
  } else {
    parsed = value as PredicateNode;
  }

  const nlText = predicateToNaturalLanguage(parsed);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowJson(!showJson)}
          className="text-[10px] font-medium text-blue-600 hover:text-blue-800 uppercase tracking-wide"
          data-testid="toggle-json"
        >
          {showJson ? "Show Natural Language" : "Show JSON"}
        </button>
      </div>
      {showJson ? (
        <div className="bg-slate-50 border border-slate-200 rounded p-3 space-y-0.5">
          <PredicateTree node={parsed} />
        </div>
      ) : (
        <div
          className="bg-slate-50 border border-slate-200 rounded p-3 text-sm text-slate-800 leading-relaxed"
          data-testid="nl-predicate"
        >
          {nlText}
        </div>
      )}
    </div>
  );
}

// ── Generic property renderer ──────────────────────────────────────

function PropertyValue({ value, propKey }: { value: unknown; propKey?: string }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-400 italic">null</span>;
  }

  // Special rendering for structured_eligibility.
  if (propKey === "structured_eligibility") {
    return <EligibilityBlock value={value} />;
  }

  if (typeof value === "object") {
    return (
      <pre className="bg-white border border-slate-200 rounded p-2 text-xs leading-relaxed overflow-x-auto max-h-80 overflow-y-auto font-mono">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  }
  if (typeof value === "string" && value.length > 120) {
    return <p className="text-sm leading-relaxed whitespace-pre-wrap">{value}</p>;
  }
  return <span className="text-sm">{String(value)}</span>;
}

/** Provenance properties extracted and shown prominently. */
const PROVENANCE_KEYS = [
  "provenance_guideline",
  "provenance_version",
  "provenance_source_section",
  "provenance_publication_date",
  "source_guideline_id",
  "source_section",
  "effective_date",
];

/** Properties that are already displayed in the header — exclude from the properties list. */
const HEADER_KEYS = ["title", "name", "display_name"];

function ProvenanceBlock({ properties }: { properties: Record<string, unknown> }) {
  const entries = PROVENANCE_KEYS.filter((k) => k in properties).map((k) => ({
    key: k,
    value: properties[k],
  }));
  if (entries.length === 0) return null;

  return (
    <section className="mt-4 pt-4 border-t border-slate-200">
      <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
        Provenance
      </h3>
      <div className="space-y-2">
        {entries.map(({ key, value }) => (
          <div key={key}>
            <div className="text-[11px] uppercase tracking-wide font-semibold text-slate-400">
              {key.replace(/^provenance_/, "")}
            </div>
            <div className="text-sm text-slate-900">
              <PropertyValue value={value} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── Eligibility table renderer ────────────────────────────────────

/** Category labels and colors for grouping eligibility predicates. */
const PREDICATE_CATEGORIES: Record<string, { label: string; color: string }> = {
  demographics: { label: "Demographics", color: "bg-blue-50 border-blue-200" },
  conditions: { label: "Conditions", color: "bg-green-50 border-green-200" },
  risk: { label: "Risk Factors", color: "bg-amber-50 border-amber-200" },
  labs: { label: "Lab Values", color: "bg-indigo-50 border-indigo-200" },
  medications: { label: "Medications", color: "bg-pink-50 border-pink-200" },
  exclusions: { label: "Exclusions", color: "bg-red-50 border-red-200" },
};

/** Map predicate names to categories. */
function predicateCategory(name: string): string {
  if (name === "age_between" || name === "age_greater_than_or_equal" || name === "age_less_than" || name === "administrative_sex_is" || name === "has_ancestry_matching") return "demographics";
  if (name === "has_active_condition" || name === "has_condition_history") return "conditions";
  if (name === "risk_score_compares" || name === "smoking_status_is") return "risk";
  if (name === "most_recent_observation_value") return "labs";
  if (name === "has_medication_active") return "medications";
  return "conditions"; // fallback
}

interface FlatPredicate {
  category: string;
  label: string;
  detail: string;
  isExclusion: boolean;
  isAnyOf: boolean;
}

/** NL templates for table display. */
const TABLE_TEMPLATES: Record<string, (args: Record<string, unknown>) => { label: string; detail: string }> = {
  age_between: (a) => ({ label: "Age range", detail: `${a.min}–${a.max} years` }),
  age_greater_than_or_equal: (a) => ({ label: "Minimum age", detail: `≥ ${a.value} years` }),
  age_less_than: (a) => ({ label: "Maximum age", detail: `< ${a.value} years` }),
  administrative_sex_is: (a) => ({ label: "Sex", detail: String(a.value) }),
  has_ancestry_matching: (a) => ({ label: "Ancestry", detail: Array.isArray(a.populations) ? (a.populations as string[]).join(", ") : String(a.populations) }),
  has_condition_history: (a) => ({ label: "Condition history", detail: Array.isArray(a.codes) ? (a.codes as string[]).map(formatCodeForTable).join(", ") : formatCodeForTable(String(a.codes)) }),
  has_active_condition: (a) => ({ label: "Active condition", detail: Array.isArray(a.codes) ? (a.codes as string[]).map(formatCodeForTable).join(", ") : formatCodeForTable(String(a.codes)) }),
  smoking_status_is: (a) => ({ label: "Smoking status", detail: Array.isArray(a.values) ? (a.values as string[]).map(v => v.replace(/_/g, " ")).join(", ") : String(a.values) }),
  most_recent_observation_value: (a) => {
    const comp = { eq: "=", ne: "≠", gt: ">", lt: "<", gte: "≥", lte: "≤" }[String(a.comparator)] ?? a.comparator;
    return { label: formatCodeForTable(String(a.code)), detail: `${comp} ${a.threshold} ${a.unit ?? ""}${a.window ? ` (within ${a.window})` : ""}`.trim() };
  },
  has_medication_active: (a) => ({ label: "Active medication", detail: Array.isArray(a.codes) ? (a.codes as string[]).map(formatCodeForTable).join(", ") : formatCodeForTable(String(a.codes)) }),
  risk_score_compares: (a) => {
    const comp = { eq: "=", ne: "≠", gt: ">", lt: "<", gte: "≥", lte: "≤" }[String(a.comparator)] ?? a.comparator;
    return { label: "10-year ASCVD risk", detail: `${comp} ${a.threshold}%` };
  },
};

function formatCodeForTable(code: string): string {
  return code.replace(/^(cond|med|obs|proc):/, "").replace(/-/g, " ");
}

/** Flatten a predicate tree into categorized rows. */
function flattenPredicates(
  node: PredicateNode,
  isExclusion = false,
  isAnyOf = false,
): FlatPredicate[] {
  const results: FlatPredicate[] = [];

  for (const [key, value] of Object.entries(node)) {
    if (key === "none_of" && Array.isArray(value)) {
      for (const child of value as PredicateNode[]) {
        results.push(...flattenPredicates(child, true, false));
      }
    } else if (key === "any_of" && Array.isArray(value)) {
      for (const child of value as PredicateNode[]) {
        results.push(...flattenPredicates(child, isExclusion, true));
      }
    } else if (key === "all_of" && Array.isArray(value)) {
      for (const child of value as PredicateNode[]) {
        results.push(...flattenPredicates(child, isExclusion, isAnyOf));
      }
    } else if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      const template = TABLE_TEMPLATES[key];
      const category = isExclusion ? "exclusions" : predicateCategory(key);
      if (template) {
        const { label, detail } = template(value as Record<string, unknown>);
        results.push({ category, label, detail, isExclusion, isAnyOf });
      } else {
        const args = Object.entries(value as Record<string, unknown>)
          .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
          .join(", ");
        results.push({ category, label: key, detail: args, isExclusion, isAnyOf });
      }
    }
  }

  return results;
}

function EligibilityTable({ value }: { value: unknown }) {
  const [showJson, setShowJson] = useState(false);

  if (!value) return null;

  let parsed: PredicateNode;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value) as PredicateNode;
    } catch {
      return (
        <pre className="bg-white border border-slate-200 rounded p-2 text-xs font-mono overflow-x-auto">
          {value}
        </pre>
      );
    }
  } else {
    parsed = value as PredicateNode;
  }

  const flat = flattenPredicates(parsed);

  // Group by category, preserving order.
  const grouped = new Map<string, FlatPredicate[]>();
  for (const pred of flat) {
    if (!grouped.has(pred.category)) grouped.set(pred.category, []);
    grouped.get(pred.category)!.push(pred);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowJson(!showJson)}
          className="text-[10px] font-medium text-blue-600 hover:text-blue-800 uppercase tracking-wide"
          data-testid="toggle-json"
        >
          {showJson ? "Show Table" : "Show JSON"}
        </button>
      </div>
      {showJson ? (
        <pre className="bg-slate-50 border border-slate-200 rounded p-3 text-xs font-mono overflow-x-auto max-h-80 overflow-y-auto">
          {JSON.stringify(parsed, null, 2)}
        </pre>
      ) : (
        <div className="space-y-3">
          {Array.from(grouped.entries()).map(([category, preds]) => {
            const catInfo = PREDICATE_CATEGORIES[category] ?? { label: category, color: "bg-slate-50 border-slate-200" };
            return (
              <div key={category} className={`rounded border ${catInfo.color}`}>
                <div className="px-3 py-1.5 border-b border-inherit">
                  <span className="text-[11px] uppercase tracking-wide font-semibold text-slate-600">
                    {catInfo.label}
                  </span>
                </div>
                <table className="w-full text-xs">
                  <tbody>
                    {preds.map((pred, i) => (
                      <tr key={i} className="border-b border-inherit last:border-b-0">
                        <td className="px-3 py-1.5 text-slate-600 font-medium whitespace-nowrap align-top w-1/3">
                          {pred.isAnyOf && (
                            <span className="text-amber-600 text-[10px] font-semibold mr-1">OR</span>
                          )}
                          {pred.label}
                        </td>
                        <td className="px-3 py-1.5 text-slate-900">
                          {pred.detail}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Recommendation-specific panel ────────────────────────────────

const GRADE_COLORS: Record<string, string> = {
  A: "bg-green-100 text-green-800 border-green-300",
  B: "bg-green-100 text-green-800 border-green-300",
  C: "bg-amber-100 text-amber-800 border-amber-300",
  D: "bg-red-100 text-red-800 border-red-300",
  I: "bg-slate-100 text-slate-600 border-slate-300",
};

/** Rec properties shown in the summary row, not in the generic list. */
const REC_SUMMARY_KEYS = new Set([
  "evidence_grade", "intent", "trigger", "structured_eligibility", "clinical_nuance",
  ...HEADER_KEYS, ...PROVENANCE_KEYS,
]);

function RecommendationPanel({ node }: { node: GraphNode & { domain?: string | null } }) {
  const props = node.properties;
  const displayName = (props.title as string) ?? (props.name as string) ?? node.id;
  const grade = props.evidence_grade as string | undefined;
  const intent = (props.intent as string | undefined)?.replace(/_/g, " ");
  const trigger = (props.trigger as string | undefined)?.replace(/_/g, " ");
  const nuance = props.clinical_nuance as string | undefined;
  const eligibility = props.structured_eligibility;

  const otherProps = Object.entries(props).filter(([k]) => !REC_SUMMARY_KEYS.has(k));

  return (
    <>
      <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-1">
        Recommendation
      </h3>
      <h2 className="text-base font-semibold text-slate-900 mb-2 break-words">
        {displayName}
      </h2>
      <div className="flex gap-1.5 flex-wrap mb-4">
        {node.domain && <DomainBadge domain={node.domain} />}
        {grade && (
          <span className={`inline-block px-2.5 py-0.5 text-[11px] font-semibold rounded border ${GRADE_COLORS[grade] ?? GRADE_COLORS.I}`}>
            Grade {grade}
          </span>
        )}
        {intent && (
          <span className="inline-block px-2.5 py-0.5 text-[11px] font-medium rounded border bg-slate-100 text-slate-700 border-slate-300 capitalize">
            {intent}
          </span>
        )}
        {trigger && (
          <span className="inline-block px-2.5 py-0.5 text-[11px] font-medium rounded border bg-slate-100 text-slate-700 border-slate-300 capitalize">
            {trigger}
          </span>
        )}
      </div>

      {/* Eligibility table */}
      {eligibility && (
        <section className="mb-4">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Eligibility Criteria
          </h3>
          <EligibilityTable value={eligibility} />
        </section>
      )}

      {/* Clinical nuance */}
      {nuance && (
        <section className="mb-4 border-t border-slate-200 pt-4">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Clinical Nuance
          </h3>
          <p className="text-sm text-slate-700 leading-relaxed">{nuance}</p>
        </section>
      )}

      {/* ID */}
      <div className="text-xs text-slate-400 mb-4 font-mono">{node.id}</div>

      {/* Remaining properties */}
      {otherProps.length > 0 && (
        <section className="border-t border-slate-200 pt-4">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Other Properties
          </h3>
          <div className="space-y-3">
            {otherProps.map(([key, value]) => (
              <div key={key}>
                <div className="text-[11px] uppercase tracking-wide font-semibold text-slate-400">
                  {key}
                </div>
                <div className="text-slate-900">
                  <PropertyValue value={value} propKey={key} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <ProvenanceBlock properties={props} />
    </>
  );
}

function NodePanel({ node }: { node: GraphNode & { domain?: string | null } }) {
  const displayName =
    (node.properties.title as string) ??
    (node.properties.name as string) ??
    (node.properties.display_name as string) ??
    node.id;

  // Separate provenance and header-duplicate keys from other properties.
  const otherProps = Object.entries(node.properties).filter(
    ([k]) => !PROVENANCE_KEYS.includes(k) && !HEADER_KEYS.includes(k),
  );

  return (
    <>
      <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-1">
        Node
      </h3>
      <h2 className="text-base font-semibold text-slate-900 mb-1 break-words">
        {displayName}
      </h2>
      <div className="flex gap-1.5 flex-wrap mb-3">
        {node.labels
          .filter((l) => !DOMAIN_LABELS.has(l))
          .map((l) => (
            <Badge key={l} label={l} />
          ))}
        {node.domain && <DomainBadge domain={node.domain} />}
      </div>
      <div className="text-xs text-slate-500 mb-4 font-mono">{node.id}</div>

      {node.codes && node.codes.length > 0 && (
        <section className="mb-4">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-1.5">
            Codes
          </h3>
          <div className="flex flex-wrap gap-1">
            {node.codes.map((c, i) => (
              <span
                key={i}
                className="inline-block bg-slate-100 px-2 py-0.5 rounded text-xs cursor-default"
                title={
                  c.display ??
                  `${displayName} — ${SYSTEM_NAMES[c.system] ?? c.system.toUpperCase()} ${c.code}`
                }
              >
                {c.system}:{c.code}
              </span>
            ))}
          </div>
        </section>
      )}

      {otherProps.length > 0 && (
        <section className="border-t border-slate-200 pt-4">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Properties
          </h3>
          <div className="space-y-3">
            {otherProps.map(([key, value]) => (
              <div key={key}>
                <div className="text-[11px] uppercase tracking-wide font-semibold text-slate-400">
                  {key}
                </div>
                <div className="text-slate-900">
                  <PropertyValue value={value} propKey={key} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <ProvenanceBlock properties={node.properties} />
    </>
  );
}

function EdgePanel({ edge }: { edge: GraphEdge }) {
  const propEntries = Object.entries(edge.properties);

  return (
    <>
      <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-1">
        Edge
      </h3>
      <h2 className="text-base font-semibold text-slate-900 mb-1">
        {edge.type}
      </h2>
      <div className="text-xs text-slate-500 mb-4 space-y-1">
        <div>
          <span className="font-semibold text-slate-600">From:</span>{" "}
          <span className="font-mono">{edge.start}</span>
        </div>
        <div>
          <span className="font-semibold text-slate-600">To:</span>{" "}
          <span className="font-mono">{edge.end}</span>
        </div>
      </div>

      {propEntries.length > 0 && (
        <section className="border-t border-slate-200 pt-4">
          <h3 className="text-[11px] uppercase tracking-wide font-semibold text-slate-500 mb-2">
            Properties
          </h3>
          <div className="space-y-3">
            {propEntries.map(([key, value]) => (
              <div key={key}>
                <div className="text-[11px] uppercase tracking-wide font-semibold text-slate-400">
                  {key}
                </div>
                <div className="text-slate-900">
                  <PropertyValue value={value} propKey={key} />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

export default function NodeDetail({ node, edge }: NodeDetailProps) {
  if (!node && !edge) {
    return (
      <div className="text-slate-400 italic text-sm px-5 pt-10 text-center">
        Click a node or edge to see details.
      </div>
    );
  }

  return (
    <div className="p-5 overflow-y-auto h-full" data-testid="node-detail">
      {node && (node.labels.includes("Recommendation") ? <RecommendationPanel node={node} /> : <NodePanel node={node} />)}
      {!node && edge && <EdgePanel edge={edge} />}
    </div>
  );
}
