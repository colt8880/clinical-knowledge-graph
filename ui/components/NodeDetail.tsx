"use client";

import type { GraphNode, GraphEdge } from "@/lib/api/client";

interface NodeDetailProps {
  node: GraphNode | null;
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

  return (
    <div className="bg-slate-50 border border-slate-200 rounded p-3 space-y-0.5">
      <PredicateTree node={parsed} />
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

function NodePanel({ node }: { node: GraphNode }) {
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
        {node.labels.map((l) => (
          <Badge key={l} label={l} />
        ))}
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
      {node && <NodePanel node={node} />}
      {!node && edge && <EdgePanel edge={edge} />}
    </div>
  );
}
