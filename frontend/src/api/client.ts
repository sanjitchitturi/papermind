const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export interface Paper {
  id: string;
  title: string;
  authors: string;
  year: number | null;
  arxiv_id: string | null;
  abstract: string;
  num_pages: number;
  num_chunks: number;
  source: string;
}

export interface ArxivSearchResult {
  arxiv_id: string;
  title: string;
  authors: string[];
  abstract: string;
  published: string | null;
}

export interface Job {
  job_id: string;
  kind: string;
  status: "queued" | "running" | "done" | "failed";
  stage: string;
  progress: number;
  message: string;
  error: string | null;
  paper_id: string | null;
  result: Record<string, unknown>;
}

export interface Source {
  index: number;
  paper_id: string;
  paper_title: string;
  section: string;
  page: number;
  text: string;
}

export interface TrustSignals {
  retrieval_margin: number;
  rerank_confidence: number;
  citation_pass_rate: number;
  self_consistency: number;
  n_sources: number;
  generative: boolean;
}

export interface ChatResponse {
  answer_id: string;
  answer: string;
  mode: string;
  sources: Source[];
  trust_score: number;
  trust_explanation: string;
  trust_signals: TrustSignals;
  abstained: boolean;
  latency_ms: number;
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
  evidence_section: string;
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
  kind: string;
  label: string;
  type: string;
  paper_id: string;
  year?: number | null;
  arxiv_id?: string | null;
  mentions?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface EvalRunSummary {
  id: string;
  suite: string;
  commit_sha: string;
  config: Record<string, unknown>;
  metrics: Record<string, number>;
  created_at: string;
}

export interface Capabilities {
  embedding_model: string;
  embedding_description: string;
  embedding_dim: number | null;
  reranker_model: string;
  reranker_description: string;
  llm_configured: boolean;
  llm_model: string | null;
  llm_host: string | null;
  papers: number;
  max_papers: number;
  chunks_indexed: number;
}

export interface Health {
  status: string;
  version: string;
  commit: string;
  postgres: boolean;
  qdrant: boolean;
  llm: boolean;
}

export const api = {
  health: () => request<Health>("/health"),
  capabilities: () => request<Capabilities>("/capabilities"),

  listPapers: () => request<Paper[]>("/papers"),
  deletePaper: (id: string) => request<{ deleted: string }>(`/papers/${id}`, { method: "DELETE" }),

  searchArxiv: (query: string, maxResults = 8) =>
    request<ArxivSearchResult[]>("/ingest/arxiv/search", {
      method: "POST",
      body: JSON.stringify({ query, max_results: maxResults }),
    }),

  ingestArxiv: (arxivId: string) =>
    request<Job>("/ingest/arxiv", { method: "POST", body: JSON.stringify({ arxiv_id: arxivId }) }),

  uploadPdf: async (file: File): Promise<Job> => {
    const formData = new FormData();
    formData.append("file", file);
    return request<Job>("/ingest/upload", { method: "POST", body: formData });
  },

  getJob: (jobId: string) => request<Job>(`/ingest/jobs/${jobId}`),

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
    request<ResearchResponse>("/research", { method: "POST", body: JSON.stringify({ question }) }),

  runIntegrityCheck: (paperId: string) => request<Job>(`/integrity/papers/${paperId}/check`, { method: "POST" }),
  getIntegrityReport: (paperId: string) => request<IntegrityReport>(`/integrity/papers/${paperId}/report`),
  scanContradictions: () => request<Job>("/integrity/contradictions/scan", { method: "POST" }),
  listContradictions: () => request<ContradictionRow[]>("/integrity/contradictions"),

  buildGraphForPaper: (paperId: string) =>
    request<{ entities: number; citations: number }>(`/graph/papers/${paperId}/build`, { method: "POST" }),
  getGraph: () => request<GraphData>("/graph"),

  runEval: (suite = "retrieval") => request<Job>(`/eval/run?suite=${suite}`, { method: "POST" }),
  getEvalHistory: () => request<EvalRunSummary[]>("/eval/history"),
};

export async function pollJob(jobId: string, onTick?: (job: Job) => void, intervalMs = 1200): Promise<Job> {
  for (;;) {
    const job = await api.getJob(jobId);
    onTick?.(job);
    if (job.status === "done" || job.status === "failed") return job;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
