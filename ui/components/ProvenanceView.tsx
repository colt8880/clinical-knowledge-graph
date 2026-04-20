"use client";

import type { GuidelineMeta } from "@/lib/api/client";

interface ProvenanceViewProps {
  guideline: GuidelineMeta;
}

export default function ProvenanceView({ guideline }: ProvenanceViewProps) {
  return (
    <div
      className="p-6 max-w-3xl"
      role="tabpanel"
      id="panel-provenance"
      data-testid="provenance-view"
    >
      <h2 className="text-base font-semibold text-slate-900 mb-4">
        Provenance
      </h2>

      <table className="w-full text-sm">
        <tbody>
          <Row label="Domain" value={guideline.domain ?? "Unknown"} />
          <Row label="Title" value={guideline.title} />
          <Row label="Version" value={guideline.version} />
          <Row label="Publication date" value={guideline.publication_date} />
          <Row
            label="Citation URL"
            value={
              guideline.citation_url ? (
                <a
                  href={guideline.citation_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline break-all"
                  data-testid="citation-url"
                >
                  {guideline.citation_url}
                </a>
              ) : (
                <span className="text-slate-400 italic">Not available</span>
              )
            }
          />
          <Row
            label="Seed hash (SHA-256)"
            value={
              guideline.seed_hash ? (
                <code className="text-xs font-mono text-slate-600 break-all" data-testid="seed-hash">
                  {guideline.seed_hash}
                </code>
              ) : (
                <span className="text-slate-400 italic">Not available</span>
              )
            }
          />
          <Row
            label="Last updated in graph"
            value={guideline.last_updated_in_graph}
          />
          <Row
            label="Recommendation count"
            value={String(guideline.rec_count)}
          />
        </tbody>
      </table>
    </div>
  );
}

function Row({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <tr className="border-b border-slate-100">
      <td className="py-2.5 pr-4 text-slate-500 font-medium align-top w-[180px]">
        {label}
      </td>
      <td className="py-2.5 text-slate-900">{value}</td>
    </tr>
  );
}
