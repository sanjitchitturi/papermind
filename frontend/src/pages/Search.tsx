import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  pollJob,
  type ArxivSearchResult,
  type Job,
  type Paper,
} from "../api/client";
import {
  Button,
  Empty,
  ErrorText,
  Input,
  Page,
  PageHeader,
  Progress,
} from "../components/ui";

export function Search() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ArxivSearchResult[]>([]);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [searched, setSearched] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPapers = useCallback(() => {
    api
      .listPapers()
      .then(setPapers)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not load papers."),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadPapers();
  }, [loadPapers]);

  async function runSearch() {
    if (!query.trim() || searching) return;
    setSearching(true);
    setError(null);
    try {
      setResults(await api.searchArxiv(query));
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function track(job: Job) {
    if (job.status === "done") {
      loadPapers();
      window.dispatchEvent(new Event("library-updated"));
      setJobs((prev) => [job, ...prev.filter((j) => j.job_id !== job.job_id)]);
      return;
    }
    setJobs((prev) => [job, ...prev.filter((j) => j.job_id !== job.job_id)]);
    const finished = await pollJob(job.job_id, (tick) => {
      setJobs((prev) => prev.map((j) => (j.job_id === tick.job_id ? tick : j)));
    });
    setJobs((prev) =>
      prev.map((j) => (j.job_id === finished.job_id ? finished : j)),
    );
    if (finished.status === "done") {
      loadPapers();
      window.dispatchEvent(new Event("library-updated"));
    }
    if (finished.status === "failed") setError(finished.error || "Job failed");
  }

  async function ingest(arxivId: string) {
    if (pending) return;
    setPending(arxivId);
    setError(null);
    try {
      await track(await api.ingestArxiv(arxivId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setPending(null);
    }
  }

  async function uploadFile(file: File) {
    if (pending) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setError("Choose a PDF smaller than 25 MB.");
      return;
    }
    setPending("upload");
    setError(null);
    try {
      await track(await api.uploadPdf(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setPending(null);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await uploadFile(file);
    e.target.value = "";
  }

  async function remove(id: string, title: string) {
    if (
      pending ||
      !window.confirm(
        `Remove “${title}” and its indexed passages from this workspace?`,
      )
    )
      return;
    setPending(id);
    setError(null);
    try {
      await api.deletePaper(id);
      loadPapers();
      window.dispatchEvent(new Event("library-updated"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setPending(null);
    }
  }

  return (
    <Page>
      <PageHeader title="Library">
        Your reading desk. Add a PDF for local keyword retrieval, or find a
        paper on arXiv with an internet connection. An arXiv ID already in the
        library is skipped.
      </PageHeader>

      <ErrorText error={error} />

      <section>
        <h2 className="mb-3 font-serif text-xl text-neutral-950">
          Search arXiv
        </h2>
        <div className="flex gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
            placeholder="e.g. retrieval augmented generation"
            aria-label="arXiv search"
          />
          <Button onClick={runSearch} disabled={searching || !query.trim()}>
            {searching ? "Searching..." : "Search"}
          </Button>
        </div>
        {searched && !searching && results.length === 0 && (
          <p role="status" className="mt-4 text-sm text-neutral-500">
            No papers matched. Try a different title or keyword.
          </p>
        )}
        <div className="mt-4 flex flex-col gap-3">
          {results.map((paper) => (
            <article
              key={paper.arxiv_id}
              className="border border-neutral-200 p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-serif text-base text-neutral-950">
                    {paper.title}
                  </p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {paper.authors.slice(0, 4).join(", ")}
                    {paper.authors.length > 4 ? " et al." : ""} ·{" "}
                    {paper.arxiv_id}
                    {paper.published ? ` · ${paper.published.slice(0, 4)}` : ""}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-neutral-700">
                    {paper.abstract.slice(0, 280)}
                    {paper.abstract.length > 280 ? "..." : ""}
                  </p>
                </div>
                <Button
                  variant="secondary"
                  disabled={!!pending}
                  onClick={() => ingest(paper.arxiv_id)}
                >
                  {pending === paper.arxiv_id ? "Adding…" : "Add"}
                </Button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 font-serif text-xl text-neutral-950">
          Upload a PDF
        </h2>
        <label
          className={`flex cursor-pointer flex-col items-start gap-2 border border-dashed px-4 py-8 text-sm ${
            dragging ? "border-neutral-950 bg-neutral-50" : "border-neutral-300"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) void uploadFile(file);
          }}
        >
          <span className="font-medium text-neutral-950">
            Drop a PDF here, or click to choose
          </span>
          <span className="text-neutral-500">
            PDF text is parsed locally. Up to 25 MB; scanned images need OCR
            before upload.
          </span>
          <input
            type="file"
            disabled={!!pending}
            accept="application/pdf"
            onChange={onUpload}
            className="mt-2 block w-full text-xs"
          />
        </label>
      </section>

      {jobs.length > 0 && (
        <section>
          <h2 className="mb-3 font-serif text-xl text-neutral-950">Jobs</h2>
          <div className="flex flex-col gap-2">
            {jobs.map((job) => (
              <div
                key={job.job_id}
                className="border border-neutral-200 px-3 py-3 text-sm"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-neutral-700">
                    {job.message || job.stage}
                  </span>
                  <span
                    className={
                      job.status === "failed"
                        ? "font-medium underline"
                        : "font-medium"
                    }
                  >
                    {job.status}
                  </span>
                </div>
                <Progress value={job.progress} />
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="mb-3 font-serif text-xl text-neutral-950">
          In the library
        </h2>
        {loading ? (
          <p role="status" className="text-sm text-neutral-500">
            Loading your library…
          </p>
        ) : papers.length === 0 ? (
          <Empty>
            Your library is ready for its first paper. Upload a PDF, search
            arXiv, or try the sample notes from the home page.
          </Empty>
        ) : (
          <div className="flex flex-col gap-2">
            {papers.map((paper) => (
              <div
                key={paper.id}
                className="flex flex-col items-start justify-between gap-4 rounded-lg border border-neutral-200 bg-white p-4 sm:flex-row"
              >
                <div>
                  <p className="font-serif text-neutral-950">{paper.title}</p>
                  <p className="mt-1 text-xs text-neutral-500">
                    {paper.authors}
                    {paper.year ? ` · ${paper.year}` : ""}
                    {paper.arxiv_id ? ` · ${paper.arxiv_id}` : ""} ·{" "}
                    {paper.num_chunks} passages{" "}
                    {paper.source === "sample" ? "· Sample note" : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <Link
                    to={`/chat?paper=${encodeURIComponent(paper.id)}`}
                    className="text-xs underline text-neutral-700 hover:text-neutral-950"
                  >
                    Ask
                  </Link>
                  <button
                    type="button"
                    disabled={!!pending}
                    onClick={() => remove(paper.id, paper.title)}
                    className="text-xs text-neutral-400 hover:text-neutral-950"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </Page>
  );
}
