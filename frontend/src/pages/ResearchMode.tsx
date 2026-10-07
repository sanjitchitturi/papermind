import { useState } from "react";
import { api, type ResearchResponse } from "../api/client";
import { ReasoningTrace } from "../components/ReasoningTrace";

export function ResearchMode() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const response = await api.research(question);
      setResult(response);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-12">
      <div>
        <h2 className="mb-2 font-serif text-2xl text-neutral-950">Research mode</h2>
        <p className="mb-4 text-sm text-neutral-600">
          Ask a broad question that spans multiple papers. The agent breaks it down, retrieves evidence across the
          corpus, and synthesizes a literature review with a comparison table.
        </p>
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="e.g. How do these papers approach few-shot learning differently?"
            className="flex-1 border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 placeholder:text-neutral-400"
          />
          <button
            onClick={run}
            disabled={loading}
            className="border border-neutral-950 bg-neutral-950 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-40"
          >
            {loading ? "Researching..." : "Run"}
          </button>
        </div>
      </div>

      {result && (
        <div className="flex flex-col gap-8">
          <ReasoningTrace trace={result.trace} />

          <div>
            <h3 className="mb-2 font-serif text-lg text-neutral-950">Literature review</h3>
            <p className="whitespace-pre-wrap text-neutral-800">{result.narrative}</p>
          </div>

          <div>
            <h3 className="mb-2 font-serif text-lg text-neutral-950">Comparison matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-neutral-950 text-left text-neutral-500">
                    <th className="p-2 font-medium">Paper</th>
                    <th className="p-2 font-medium">Method</th>
                    <th className="p-2 font-medium">Dataset</th>
                    <th className="p-2 font-medium">Metric / result</th>
                    <th className="p-2 font-medium">Limitations</th>
                  </tr>
                </thead>
                <tbody>
                  {result.matrix.map((row) => (
                    <tr key={row.paper_id} className="border-b border-neutral-200 align-top">
                      <td className="p-2 font-medium text-neutral-950">{row.paper_title}</td>
                      <td className="p-2 text-neutral-700">{row.method}</td>
                      <td className="p-2 text-neutral-700">{row.dataset}</td>
                      <td className="p-2 text-neutral-700">{row.metric_result}</td>
                      <td className="p-2 text-neutral-700">{row.limitations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
