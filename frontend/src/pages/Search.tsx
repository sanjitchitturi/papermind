import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, pollJob, type ArxivSearchResult, type Job, type Paper } from "../api/client";
import { Button, Empty, ErrorText, Input, Page, PageHeader } from "../components/ui";

export function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ArxivSearchResult[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPapers = useCallback(() => {
    api.listPapers().then(setPapers).catch(() => setPapers([]));
  }, []);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  async function runSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      setResults(await api.searchArxiv(query));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function track(job: Job) {
    if (job.status === "done") {
      loadPapers();
      setJobs((prev) => [job, ...prev.filter((j) => j.job_id !== job.job_id)]);
      return;
    }
    setJobs((prev) => [job, ...prev.filter((j) => j.job_id !== job.job_id)]);
    const finished = await pollJob(job.job_id, (tick) => {
      setJobs((prev) => prev.map((j) => (j.job_id === tick.job_id ? tick : j)));
    });
    setJobs((prev) => prev.map((j) => (j.job_id === finished.job_id ? finished : j)));
    if (finished.status === "done") loadPapers();
  }

  async function ingest(arxivId: string) {
    setError(null);
    try {
      await track(await api.ingestArxiv(arxivId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      await track(await api.uploadPdf(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <Page>
      <PageHeader title="Library">
        Search arXiv or upload a PDF. Ingestion parses sections, chunks at sentence boundaries, and indexes
        dense plus BM25 vectors locally. Duplicate arXiv ids are skipped.
      </PageHeader>

      <ErrorText error={error} />

      <section>
        <h2 className="mb-3 font-serif text-xl text-neutral-950">Search arXiv</h2>
        <div className="flex gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
            placeholder="e.g. retrieval augmented generation"
          />
          <Button onClick={runSearch} disabled={searching}>
            {searching ? "Searching..." : "Search"}
          </Button>
        </div>
        <div className="mt-4 flex flex-col gap-3">
          {results.map((paper) => (
            <article key={paper.arxiv_id} className="border border-neutral-200 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-serif text-base text-neutral-950">{paper.title}</p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {paper.authors.slice(0, 4).join(", ")}
                    {paper.authors.length > 4 ? " et al." : ""} · {paper.arxiv_id}
                  </p>
                  <p className="mt-2 text-sm text-neutral-700">{paper.abstract.slice(0, 240)}...</p>
                </div>
                <Button variant="secondary" onClick={() => ingest(paper.arxiv_id)}>
                  Ingest
                </Button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-serif text-xl text-neutral-950">Upload a PDF</h2>
        <input type="file" accept="application/pdf" onChange={onUpload} className="text-sm text-neutral-700" />
      </section>

      {jobs.length > 0 && (
        <section>
          <h2 className="mb-3 font-serif text-xl text-neutral-950">Jobs</h2>
          <div className="flex flex-col gap-2">
            {jobs.map((job) => (
              <div key={job.job_id} className="flex items-center justify-between border border-neutral-200 px-3 py-2 text-sm">
                <span className="text-neutral-700">{job.message || job.stage}</span>
                <span className="text-xs text-neutral-500">{Math.round(job.progress * 100)}%</span>
                <span className={job.status === "failed" ? "font-medium underline" : "font-medium"}>{job.status}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 font-serif text-xl text-neutral-950">In the library</h2>
        {papers.length === 0 ? (
          <Empty>Nothing ingested yet. Search arXiv above or upload a PDF.</Empty>
        ) : (
          <div className="flex flex-col gap-2">
            {papers.map((paper) => (
              <div key={paper.id} className="flex items-start justify-between gap-4 border border-neutral-200 p-3">
                <div>
                  <p className="font-serif text-neutral-950">{paper.title}</p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {paper.authors} {paper.year ? `· ${paper.year}` : ""} · {paper.num_chunks} chunks
                  </p>
                </div>
                <Link to="/chat" className="text-xs underline text-neutral-700 hover:text-neutral-950">
                  Ask
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>
    </Page>
  );
}
