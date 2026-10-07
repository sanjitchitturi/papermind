/**
 * Thin fetch wrapper for the backend API. Kept deliberately simple, no
 * axios dependency, since every call here is a plain JSON request or
 * response and fetch handles that fine on its own.
 */

// In local dev this stays "/api" and the Vite dev server proxy in
// vite.config.ts forwards it to the backend. In production, the frontend
// and backend are deployed to different hosts (Vercel vs. Render/Fly.io),
// so VITE_API_BASE_URL needs to point at the deployed backend directly.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Request to ${path} failed with ${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export interface ArxivSearchResult {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published: string | null;
}

export interface IngestionJob {
  job_id: string;
  status?: "queued" | "running" | "done" | "failed";
  stage?: string;
  error?: string | null;
  paper_id?: string | null;
}

export interface Source {
  index: number;
  paper_id: string;
  paper_title: string;
  section: string;
  text: string;
}

export interface ChatResponse {
  answer_id: string;
  answer: string;
  sources: Source[];
  trust_score: number;
  trust_explanation: string;
  abstained: boolean;
}

export interface MatrixRow {
  paper_title: string;
  paper_id: string;
  method: string;
  dataset: string;
  metric_result: string;
  limitations: string;
}

export interface TraceStep {
  kind: string;
  detail: string;
}

export interface ResearchResponse {
  narrative: string;
  matrix: MatrixRow[];
  trace: TraceStep[];
}

export interface IntegrityCitationRow {
  claim: string;
  citation_marker: string | null;
  cited_reference: string;
  verdict: string;
  evidence: string;
  rationale: string;
}

export interface IntegrityReport {
  paper_id: string;
  integrity_score: number | null;
  citations: IntegrityCitationRow[];
}

export interface ContradictionRow {
  claim_a: string;
  claim_b: string;
  explanation: string;
  confidence: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  paper_id: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface EvalRunSummary {
  id: string;
  commit_sha: string;
  pipeline_config: string;
  metrics: Record<string, number>;
  created_at: string;
}

export const api = {
  searchArxiv: (query: string, maxResults = 10) =>
    request<ArxivSearchResult[]>("/ingest/arxiv/search", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults }),
    }),

  ingestArxiv: (arxivId: string) =>
    request<IngestionJob>("/ingest/arxiv", {
      method: "POST",
      body: JSON.stringify({ arxiv_id: arxivId }),
    }),

  uploadPdf: async (file: File): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${BASE_URL}/ingest/upload`, { method: "POST", body: formData });
    if (!response.ok) {
      throw new Error(`Upload failed with ${response.status}`);
    }
    return response.json();
  },

  getJobStatus: (jobId: string) => request<IngestionJob>(`/ingest/jobs/${jobId}`),

  chat: (question: string, paperId?: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, paper_id: paperId ?? null }),
    }),

  sendFeedback: (answerId: string, rating: 1 | -1, comment?: string) =>
    request<{ feedback_id: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify({ answer_id: answerId, rating, comment: comment ?? null }),
    }),

  research: (question: string) =>
    request<ResearchResponse>("/research", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  runIntegrityCheck: (paperId: string) =>
    request<{ checked: number }>(`/integrity/papers/${paperId}/check`, { method: "POST" }),

  getIntegrityReport: (paperId: string) => request<IntegrityReport>(`/integrity/papers/${paperId}/report`),

  scanContradictions: () => request<{ found: number }>("/integrity/contradictions/scan", { method: "POST" }),

  listContradictions: () => request<ContradictionRow[]>("/integrity/contradictions"),

  buildGraphForPaper: (paperId: string) =>
    request<{ entities_created: number; citation_edges_linked: number }>(`/graph/papers/${paperId}/build`, {
      method: "POST",
    }),

  getGraph: () => request<GraphData>("/graph"),

  runEval: (pipelineConfig = "full") =>
    request<{ run_id: string; metrics: Record<string, number> }>(`/eval/run?pipeline_config=${pipelineConfig}`, {
      method: "POST",
    }),

  getEvalHistory: () => request<EvalRunSummary[]>("/eval/history"),
};
