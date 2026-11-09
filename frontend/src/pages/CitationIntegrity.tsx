import { useEffect, useState } from "react";
import {
  api,
  pollJob,
  type ContradictionRow,
  type IntegrityReport,
  type Paper,
} from "../api/client";
import {
  Button,
  Empty,
  ErrorText,
  Page,
  PageHeader,
  Select,
} from "../components/ui";

const VERDICT_STYLES: Record<string, string> = {
  supported: "font-semibold text-neutral-950",
  partially_supported: "font-medium italic text-neutral-700",
  unsupported: "font-semibold underline text-neutral-950",
  contradicted: "font-bold underline text-neutral-950",
  unresolved: "italic text-neutral-400",
};

export function CitationIntegrity() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [paperId, setPaperId] = useState("");
  const [report, setReport] = useState<IntegrityReport | null>(null);
  const [contradictions, setContradictions] = useState<ContradictionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listPapers()
      .then((list) => {
        setPapers(list);
        if (list[0]) setPaperId(list[0].id);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Could not load papers."),
      );
    api
      .listContradictions()
      .then(setContradictions)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Could not load contradictions.",
        ),
      );
  }, []);

  useEffect(() => {
    setReport(null);
    let active = true;
    if (paperId)
      api
        .getIntegrityReport(paperId)
        .then((value) => {
          if (active) setReport(value);
        })
        .catch((err) => {
          if (active)
            setError(
              err instanceof Error ? err.message : "Could not load the report.",
            );
        });
    return () => {
      active = false;
    };
  }, [paperId]);

  async function checkPaper() {
    if (!paperId) return;
    setLoading(true);
    setError(null);
    try {
      const job = await api.runIntegrityCheck(paperId);
      const done = await pollJob(job.job_id);
      if (done.status === "failed")
        throw new Error(done.error || "Check failed");
      setReport(await api.getIntegrityReport(paperId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Integrity check failed");
    } finally {
      setLoading(false);
    }
  }

  async function scanCorpus() {
    setLoading(true);
    setError(null);
    try {
      const job = await api.scanContradictions();
      const done = await pollJob(job.job_id);
      if (done.status === "failed")
        throw new Error(done.error || "Scan failed");
      setContradictions(await api.listContradictions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Page>
      <PageHeader title="Citation integrity">
        For each in-text citation, the attributed claim is compared with a
        passage from the cited paper, when that paper is in the library. This
        optional check needs a configured language model. Its verdicts are
        suggestions for human review, not proof.
      </PageHeader>
      <ErrorText error={error} />

      <section>
        <h2 className="mb-3 font-serif text-xl">Per-paper check</h2>
        <div className="flex gap-2">
          <Select
            aria-label="Paper to check"
            disabled={loading || papers.length === 0}
            value={paperId}
            onChange={(e) => setPaperId(e.target.value)}
            className="flex-1"
          >
            {papers.length === 0 && (
              <option value="">Add a paper to your library first</option>
            )}
            {papers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </Select>
          <Button onClick={checkPaper} disabled={loading || !paperId}>
            {loading ? "Checking..." : "Run check"}
          </Button>
        </div>

        {report && (
          <div className="mt-6 flex flex-col gap-3">
            {report.integrity_score !== null && (
              <p className="text-sm">
                Model-assisted result:{" "}
                <span className="font-semibold">{report.integrity_score}%</span>{" "}
                of resolvable citations were fully supported.
              </p>
            )}
            {report.citations.length === 0 && (
              <Empty>No citation claims stored for this paper yet.</Empty>
            )}
            {report.citations.map((row, i) => (
              <div key={i} className="border border-neutral-200 p-3 text-sm">
                <p className="text-neutral-800">
                  Claim: <span className="italic">"{row.claim}"</span>
                </p>
                <p className="mt-1 text-xs text-neutral-500">
                  [{row.citation_marker}]{" "}
                  {row.cited_reference || "cited work not in library"}
                  {row.evidence_section
                    ? ` · evidence: ${row.evidence_section}`
                    : ""}
                </p>
                <p
                  className={`mt-1 ${VERDICT_STYLES[row.verdict] ?? "text-neutral-600"}`}
                >
                  {row.verdict.replace(/_/g, " ")}
                </p>
                {row.rationale && (
                  <p className="mt-1 text-xs text-neutral-500">
                    {row.rationale}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 font-serif text-xl">Corpus contradictions</h2>
        <Button onClick={scanCorpus} disabled={loading || papers.length < 2}>
          Scan corpus
        </Button>
        <p className="mt-3 text-xs text-neutral-500">
          Requires at least two papers and a language model. Results need manual
          review.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          {contradictions.length === 0 && (
            <Empty>No stored contradiction candidates.</Empty>
          )}
          {contradictions.map((row, i) => (
            <div key={i} className="border border-neutral-950 p-3 text-sm">
              <p className="text-[10px] font-semibold uppercase tracking-wide">
                Contradiction
              </p>
              <p className="mt-2">A: "{row.claim_a}"</p>
              <p className="mt-1">B: "{row.claim_b}"</p>
              <p className="mt-2 text-neutral-700">{row.explanation}</p>
            </div>
          ))}
        </div>
      </section>
    </Page>
  );
}
