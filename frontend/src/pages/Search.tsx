import { useEffect, useRef, useState } from "react";
import { api, type ArxivSearchResult, type IngestionJob } from "../api/client";

export function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ArxivSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [jobs, setJobs] = useState<Record<string, IngestionJob>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function runSearch() {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const found = await api.searchArxiv(query);
      setResults(found);
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  }

  function trackJob(job: IngestionJob) {
    setJobs((prev) => ({ ...prev, [job.job_id]: job }));
  }

  async function ingestArxivPaper(arxivId: string) {
    const job = await api.ingestArxiv(arxivId);
    trackJob(job);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const job = await api.uploadPdf(file);
    trackJob(job);
  }

  // Poll every running job until it reaches a terminal state. A single
  // interval that re-checks all jobs is simpler than one timer per job
  // and is plenty responsive for a handful of concurrent ingestions.
  useEffect(() => {
    pollRef.current = setInterval(async () => {
      const activeJobIds = Object.values(jobs)
        .filter((j) => j.status !== "done" && j.status !== "failed")
        .map((j) => j.job_id);
      for (const jobId of activeJobIds) {
        const updated = await api.getJobStatus(jobId);
        trackJob(updated);
      }
    }, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobs]);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 p-6">
      <section>
        <h2 className="mb-2 text-lg font-semibold">Search arXiv</h2>
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
            placeholder="e.g. retrieval augmented generation"
            className="flex-1 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm"
          />
          <button
            onClick={runSearch}
            disabled={searching}
            className="rounded bg-blue-700 px-4 py-2 text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
          >
            {searching ? "Searching..." : "Search"}
          </button>
        </div>

        <div className="mt-4 flex flex-col gap-2">
          {results.map((paper) => (
            <div key={paper.arxiv_id} className="rounded border border-gray-700 bg-gray-900 p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{paper.title}</p>
                  <p className="text-xs text-gray-400">{paper.authors.join(", ")}</p>
                  <p className="mt-1 text-sm text-gray-300">{paper.abstract.slice(0, 220)}...</p>
                </div>
                <button
                  onClick={() => ingestArxivPaper(paper.arxiv_id)}
                  className="shrink-0 rounded border border-blue-600 px-3 py-1 text-xs text-blue-300 hover:bg-blue-900"
                >
                  Ingest
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Or upload a PDF</h2>
        <input type="file" accept="application/pdf" onChange={handleUpload} className="text-sm" />
      </section>

      {Object.keys(jobs).length > 0 && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">Ingestion jobs</h2>
          <div className="flex flex-col gap-2">
            {Object.values(jobs).map((job) => (
              <div key={job.job_id} className="flex items-center justify-between rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm">
                <span className="font-mono text-xs text-gray-400">{job.job_id.slice(0, 8)}</span>
                <span>{job.stage ?? "queued"}</span>
                <span
                  className={
                    job.status === "done"
                      ? "text-green-400"
                      : job.status === "failed"
                        ? "text-red-400"
                        : "text-yellow-400"
                  }
                >
                  {job.status ?? "queued"}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
