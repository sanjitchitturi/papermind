import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type EvalRunSummary } from "../api/client";

export function EvalDashboard() {
  const [history, setHistory] = useState<EvalRunSummary[]>([]);
  const [running, setRunning] = useState(false);

  async function load() {
    const runs = await api.getEvalHistory();
    setHistory(runs);
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  async function triggerRun(pipelineConfig: string) {
    setRunning(true);
    try {
      await api.runEval(pipelineConfig);
      await load();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
    }
  }

  const chartData = history.map((run) => ({
    label: `${run.commit_sha.slice(0, 7)} (${run.pipeline_config})`,
    hit_rate: run.metrics.retrieval_hit_rate,
    mrr: run.metrics.retrieval_mrr,
    keyword_match: run.metrics.answer_keyword_match,
    citation_pass_rate: run.metrics.citation_pass_rate,
  }));

  const latest = history[history.length - 1];

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Eval dashboard</h2>
        <div className="flex gap-2">
          <button
            onClick={() => triggerRun("baseline")}
            disabled={running}
            className="rounded border border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-800 disabled:opacity-50"
          >
            Run baseline
          </button>
          <button
            onClick={() => triggerRun("full")}
            disabled={running}
            className="rounded bg-blue-700 px-3 py-1.5 text-sm hover:bg-blue-600 disabled:opacity-50"
          >
            Run full pipeline
          </button>
        </div>
      </div>

      {latest && (
        <div className="grid grid-cols-4 gap-3">
          {Object.entries(latest.metrics)
            .filter(([key]) => key !== "num_questions")
            .map(([key, value]) => (
              <div key={key} className="rounded border border-gray-700 bg-gray-900 p-3">
                <p className="text-xs text-gray-400">{key.replace(/_/g, " ")}</p>
                <p className="text-xl font-semibold">{(value * 100).toFixed(1)}%</p>
              </div>
            ))}
        </div>
      )}

      <div className="h-80 rounded border border-gray-800 bg-gray-900 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="label" stroke="#9ca3af" fontSize={11} />
            <YAxis domain={[0, 1]} stroke="#9ca3af" fontSize={11} />
            <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151" }} />
            <Legend />
            <Line type="monotone" dataKey="hit_rate" stroke="#2563eb" />
            <Line type="monotone" dataKey="mrr" stroke="#16a34a" />
            <Line type="monotone" dataKey="keyword_match" stroke="#d97706" />
            <Line type="monotone" dataKey="citation_pass_rate" stroke="#9333ea" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-gray-500">
        "baseline" runs retrieval without query rewriting and skips reranking, useful for seeing how much the
        advanced retrieval pipeline actually improves things rather than just assuming it does.
      </p>
    </div>
  );
}
