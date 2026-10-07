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
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <div>
        <h2 className="mb-2 text-lg font-semibold">Research mode</h2>
        <p className="mb-3 text-sm text-gray-400">
          Ask a broad question that spans multiple papers. The agent breaks it down, retrieves evidence across the
          corpus, and synthesizes a literature review with a comparison table.
        </p>
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="e.g. How do these papers approach few-shot learning differently?"
            className="flex-1 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm"
          />
          <button
            onClick={run}
            disabled={loading}
            className="rounded bg-blue-700 px-4 py-2 text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? "Researching..." : "Run"}
          </button>
        </div>
      </div>

      {result && (
        <div className="flex flex-col gap-6">
          <ReasoningTrace trace={result.trace} />

          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-300">Literature review</h3>
            <p className="whitespace-pre-wrap text-gray-200">{result.narrative}</p>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-300">Comparison matrix</h3>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-left text-gray-400">
                    <th className="p-2">Paper</th>
                    <th className="p-2">Method</th>
                    <th className="p-2">Dataset</th>
                    <th className="p-2">Metric / result</th>
                    <th className="p-2">Limitations</th>
                  </tr>
                </thead>
                <tbody>
                  {result.matrix.map((row) => (
                    <tr key={row.paper_id} className="border-b border-gray-800 align-top">
                      <td className="p-2 font-medium text-gray-200">{row.paper_title}</td>
                      <td className="p-2 text-gray-300">{row.method}</td>
                      <td className="p-2 text-gray-300">{row.dataset}</td>
                      <td className="p-2 text-gray-300">{row.metric_result}</td>
                      <td className="p-2 text-gray-300">{row.limitations}</td>
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
