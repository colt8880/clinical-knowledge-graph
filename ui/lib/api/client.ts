/**
 * Typed API client for the Clinical Knowledge Graph API.
 *
 * All calls go through this module — no direct fetch() in components.
 * Types come from the generated schema.d.ts (openapi-typescript).
 */

import type { components } from "./schema";

export type GraphNode = components["schemas"]["GraphNode"];
export type GraphEdge = components["schemas"]["GraphEdge"];
export type Subgraph = components["schemas"]["Subgraph"];
export type EvalTrace = components["schemas"]["eval-trace.schema"];
export type PatientContext = components["schemas"]["patient-context.schema"];

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchNode(id: string): Promise<GraphNode> {
  return apiFetch<GraphNode>(`/nodes/${encodeURIComponent(id)}`);
}

export async function fetchNeighbors(
  id: string,
  edgeTypes?: string[],
): Promise<Subgraph> {
  const params = new URLSearchParams();
  if (edgeTypes) {
    for (const t of edgeTypes) {
      params.append("edge_types", t);
    }
  }
  const qs = params.toString();
  return apiFetch<Subgraph>(
    `/nodes/${encodeURIComponent(id)}/neighbors${qs ? `?${qs}` : ""}`,
  );
}

export async function evaluate(
  patientContext: PatientContext,
): Promise<EvalTrace> {
  return apiFetch<EvalTrace>("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_context: patientContext }),
  });
}

/** Node with domain info, as returned by GET /subgraph. */
export interface ForestNode extends GraphNode {
  domain: "USPSTF" | "ACC_AHA" | "KDIGO" | "ADA" | null;
}

export interface ForestSubgraph {
  nodes: ForestNode[];
  edges: GraphEdge[];
}

export async function fetchSubgraph(
  domains?: string[],
): Promise<ForestSubgraph> {
  const params = new URLSearchParams();
  if (domains !== undefined) {
    params.set("domains", domains.join(","));
  }
  const qs = params.toString();
  return apiFetch<ForestSubgraph>(`/subgraph${qs ? `?${qs}` : ""}`);
}

export type GuidelineMeta = components["schemas"]["GuidelineMeta"];

export async function fetchGuidelines(): Promise<GuidelineMeta[]> {
  return apiFetch<GuidelineMeta[]>("/guidelines");
}

// ── Interactions view types ─────────────────────────────────────────

export interface InteractionGuideline {
  id: string;
  domain: string;
  title: string;
}

export interface InteractionRec {
  id: string;
  title: string;
  domain: string | null;
  evidence_grade: string | null;
  has_preemption_in: boolean;
  has_preemption_out: boolean;
  modifier_count: number;
}

export interface InteractionSharedEntity {
  id: string;
  type: string;
  title: string;
}

export interface InteractionEdge {
  type: "PREEMPTED_BY" | "MODIFIES";
  source: string;
  target: string;
  edge_priority?: number;
  reason?: string;
  nature?: string;
  note?: string;
  suppressed_by_preemption?: boolean;
}

export interface InteractionsResponse {
  guidelines: InteractionGuideline[];
  recommendations: InteractionRec[];
  shared_entities: InteractionSharedEntity[];
  edges: InteractionEdge[];
}

export async function fetchInteractions(
  type: "preemption" | "modifier" | "both" = "both",
  guidelines?: string[],
): Promise<InteractionsResponse> {
  const params = new URLSearchParams();
  params.set("type", type);
  if (guidelines && guidelines.length > 0) {
    params.set("guidelines", guidelines.join(","));
  }
  return apiFetch<InteractionsResponse>(`/interactions?${params.toString()}`);
}

export async function searchNodes(
  q: string,
  nodeTypes?: string[],
  limit?: number,
): Promise<{ results: GraphNode[] }> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (nodeTypes) {
    for (const t of nodeTypes) {
      params.append("node_types", t);
    }
  }
  if (limit) params.set("limit", String(limit));
  return apiFetch<{ results: GraphNode[] }>(`/search?${params.toString()}`);
}
