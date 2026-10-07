import { useState } from "react";
import { api, type ContradictionRow, type IntegrityReport } from "../api/client";

const VERDICT_COLORS: Record<string, string> = {
  supported: "text-green-400",
  partially_supported: "text-yellow-400",
  unsupported: "text-orange-400",
  contradicted: "text-red-400",
  unresolved: "text-gray-500",
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
    <div className="mx-auto flex max-w-4xl flex-col gap-10 p-6">
      <section>
        <h2 className="mb-2 text-lg font-semibold">Per-paper citation integrity</h2>
        <p className="mb-3 text-sm text-gray-400">
          Checks whether each in-text citation in this paper is actually supported by what the cited work says.
        </p>
        <div className="flex gap-2">
          <input
            value={paperId}
            onChange={(e) => setPaperId(e.target.value)}
            placeholder="Paper id"
            className="flex-1 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm"
          />
          <button
            onClick={checkPaper}
            disabled={loading}
            className="rounded bg-blue-700 px-4 py-2 text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
          >
            Run check
          </button>
        </div>

        {report && (
          <div className="mt-4 flex flex-col gap-3">
            {report.integrity_score !== null && (
              <p className="text-sm">
                Integrity score: <span className="font-semibold">{report.integrity_score}%</span> of resolvable
                citations were fully supported.
              </p>
            )}
            {report.citations.map((row, i) => (
              <div key={i} className="rounded border border-gray-800 bg-gray-900 p-3 text-sm">
                <p className="text-gray-200">
                  Claim: <span className="italic">"{row.claim}"</span>
                </p>
                <p className="mt-1 text-xs text-gray-500">Citation [{row.citation_marker}]: {row.cited_reference}</p>
                <p className={`mt-1 font-semibold ${VERDICT_COLORS[row.verdict] ?? "text-gray-400"}`}>
                  {row.verdict.replace("_", " ")}
                </p>
                {row.rationale && <p className="mt-1 text-xs text-gray-400">{row.rationale}</p>}
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Corpus-wide contradictions</h2>
        <p className="mb-3 text-sm text-gray-400">
          Scans claims across every ingested paper for pairs that disagree on the same topic.
        </p>
        <button
          onClick={scanCorpus}
          disabled={loading}
          className="rounded bg-blue-700 px-4 py-2 text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
        >
          Scan corpus
        </button>

        <div className="mt-4 flex flex-col gap-3">
          {contradictions.map((row, i) => (
            <div key={i} className="rounded border border-red-900 bg-gray-900 p-3 text-sm">
              <p className="text-gray-200">A: "{row.claim_a}"</p>
              <p className="mt-1 text-gray-200">B: "{row.claim_b}"</p>
              <p className="mt-2 text-red-300">{row.explanation}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
