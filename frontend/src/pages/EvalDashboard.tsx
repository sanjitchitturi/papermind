import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type EvalRunSummary } from "../api/client";

// recharts needs literal stroke values, Tailwind classes don't apply to
// SVG stroke attributes. Each series gets a distinct grayscale shade AND
// a distinct dash pattern, since color alone can no longer tell them apart.
const SERIES = [
  { key: "hit_rate", stroke: "#0a0a0a", dash: undefined },
  { key: "mrr", stroke: "#404040", dash: "6 3" },
  { key: "keyword_match", stroke: "#737373", dash: "2 2" },
  { key: "citation_pass_rate", stroke: "#a3a3a3", dash: "8 3 2 3" },
] as const;

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
    <div className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-12">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-2xl text-neutral-950">Eval dashboard</h2>
        <div className="flex gap-2">
          <button
            onClick={() => triggerRun("baseline")}
            disabled={running}
            className="border border-neutral-300 px-3 py-1.5 text-sm text-neutral-800 hover:border-neutral-950 hover:text-neutral-950 disabled:opacity-40"
          >
            Run baseline
          </button>
          <button
            onClick={() => triggerRun("full")}
            disabled={running}
            className="border border-neutral-950 bg-neutral-950 px-3 py-1.5 text-sm text-white hover:bg-neutral-800 disabled:opacity-40"
          >
            Run full pipeline
          </button>
        </div>
      </div>

      {latest && (
        <div className="grid grid-cols-4 gap-px border border-neutral-200 bg-neutral-200">
          {Object.entries(latest.metrics)
            .filter(([key]) => key !== "num_questions")
            .map(([key, value]) => (
              <div key={key} className="bg-white p-4">
                <p className="text-xs text-neutral-500">{key.replace(/_/g, " ")}</p>
                <p className="font-serif text-2xl text-neutral-950">{(value * 100).toFixed(1)}%</p>
              </div>
            ))}
        </div>
      )}

      <div className="h-80 border border-neutral-200 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="2 2" stroke="#e5e5e5" />
            <XAxis dataKey="label" stroke="#a3a3a3" fontSize={11} />
            <YAxis domain={[0, 1]} stroke="#a3a3a3" fontSize={11} />
            <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #d4d4d4", color: "#0a0a0a" }} />
            <Legend />
            {SERIES.map((series) => (
              <Line key={series.key} type="monotone" dataKey={series.key} stroke={series.stroke} strokeDasharray={series.dash} dot={{ r: 2 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="text-xs text-neutral-500">
        "baseline" runs retrieval without query rewriting and skips reranking, useful for seeing how much the
        advanced retrieval pipeline actually improves things rather than just assuming it does.
      </p>
    </div>
  );
}
