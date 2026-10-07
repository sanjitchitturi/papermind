import { useState } from "react";
import { api, type ResearchResponse } from "../api/client";
import { ReasoningTrace } from "../components/ReasoningTrace";
import { Button, ErrorText, Input, Page, PageHeader } from "../components/ui";

export function ResearchMode() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      setResult(await api.research(question));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Page wide>
      <PageHeader title="Research mode">
        A broad question is decomposed, retrieved across papers, critiqued for coverage, then synthesized
        into a review plus a comparison table. The trace is visible.
      </PageHeader>
      <div className="flex gap-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="e.g. How do these papers approach few-shot learning?"
        />
        <Button onClick={run} disabled={loading}>
          {loading ? "Researching..." : "Run"}
        </Button>
      </div>
      <ErrorText error={error} />

      {loading && <p className="text-sm text-neutral-500">Decomposing, retrieving, and synthesizing...</p>}

      {result && (
        <div className="flex flex-col gap-8">
          <ReasoningTrace trace={result.trace} />
          <section>
            <h2 className="mb-2 font-serif text-lg">Literature review</h2>
            <p className="whitespace-pre-wrap leading-relaxed text-neutral-800">{result.narrative}</p>
          </section>
          <section>
            <h2 className="mb-2 font-serif text-lg">Comparison matrix</h2>
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
                      <td className="p-2 font-medium">{row.paper_title}</td>
                      <td className="p-2 text-neutral-700">{row.method}</td>
                      <td className="p-2 text-neutral-700">{row.dataset}</td>
                      <td className="p-2 text-neutral-700">{row.metric_result}</td>
                      <td className="p-2 text-neutral-700">{row.limitations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </Page>
  );
}
