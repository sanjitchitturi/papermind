import { useState } from "react";
import { api, type ContradictionRow, type IntegrityReport } from "../api/client";

// No color coding, each verdict gets a distinct text treatment instead so
// the distinction survives in a strictly monochrome UI.
const VERDICT_STYLES: Record<string, string> = {
  supported: "font-semibold text-neutral-950",
  partially_supported: "font-medium text-neutral-700 italic",
  unsupported: "font-semibold text-neutral-950 underline",
  contradicted: "font-bold text-neutral-950 underline",
  unresolved: "text-neutral-400 italic",
};

export function CitationIntegrity() {
  const [paperId, setPaperId] = useState("");
  const [report, setReport] = useState<IntegrityReport | null>(null);
  const [contradictions, setContradictions] = useState<ContradictionRow[]>([]);
  const [loading, setLoading] = useState(false);

  async function checkPaper() {
    if (!paperId.trim()) return;
    setLoading(true);
    try {
      await api.runIntegrityCheck(paperId);
      const result = await api.getIntegrityReport(paperId);
      setReport(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function scanCorpus() {
    setLoading(true);
    try {
      await api.scanContradictions();
      const rows = await api.listContradictions();
      setContradictions(rows);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-16 px-6 py-12">
      <section>
        <h2 className="mb-2 font-serif text-2xl text-neutral-950">Per-paper citation integrity</h2>
        <p className="mb-4 text-sm text-neutral-600">
          Checks whether each in-text citation in this paper is actually supported by what the cited work says.
        </p>
        <div className="flex gap-2">
          <input
            value={paperId}
            onChange={(e) => setPaperId(e.target.value)}
            placeholder="Paper id"
            className="flex-1 border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 placeholder:text-neutral-400"
          />
          <button
            onClick={checkPaper}
            disabled={loading}
            className="border border-neutral-950 bg-neutral-950 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-40"
          >
            Run check
          </button>
        </div>

        {report && (
          <div className="mt-6 flex flex-col gap-3">
            {report.integrity_score !== null && (
              <p className="text-sm text-neutral-800">
                Integrity score: <span className="font-semibold text-neutral-950">{report.integrity_score}%</span>{" "}
                of resolvable citations were fully supported.
              </p>
            )}
            {report.citations.map((row, i) => (
              <div key={i} className="border border-neutral-200 p-3 text-sm">
                <p className="text-neutral-800">
                  Claim: <span className="italic">&ldquo;{row.claim}&rdquo;</span>
                </p>
                <p className="mt-1 text-xs text-neutral-500">
                  Citation [{row.citation_marker}]: {row.cited_reference}
                </p>
                <p className={`mt-1 ${VERDICT_STYLES[row.verdict] ?? "text-neutral-600"}`}>
                  {row.verdict.replace("_", " ")}
                </p>
                {row.rationale && <p className="mt-1 text-xs text-neutral-500">{row.rationale}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 font-serif text-2xl text-neutral-950">Corpus-wide contradictions</h2>
        <p className="mb-4 text-sm text-neutral-600">
          Scans claims across every ingested paper for pairs that disagree on the same topic.
        </p>
        <button
          onClick={scanCorpus}
          disabled={loading}
          className="border border-neutral-950 bg-neutral-950 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-40"
        >
          Scan corpus
        </button>

        <div className="mt-6 flex flex-col gap-3">
          {contradictions.map((row, i) => (
            <div key={i} className="border border-neutral-950 p-3 text-sm">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-neutral-950">Contradiction</p>
              <p className="mt-2 text-neutral-800">A: &ldquo;{row.claim_a}&rdquo;</p>
              <p className="mt-1 text-neutral-800">B: &ldquo;{row.claim_b}&rdquo;</p>
              <p className="mt-2 text-neutral-950">{row.explanation}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
