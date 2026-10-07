import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, pollJob, type EvalRunSummary } from "../api/client";
import { Button, Empty, ErrorText, Page, PageHeader } from "../components/ui";

const SERIES = [
  { key: "hybrid+rerank_mrr", label: "hybrid+rerank MRR", stroke: "#0a0a0a", dash: undefined },
  { key: "hybrid_mrr", label: "hybrid MRR", stroke: "#404040", dash: "6 3" },
  { key: "dense_mrr", label: "dense MRR", stroke: "#737373", dash: "2 2" },
  { key: "sparse_mrr", label: "sparse MRR", stroke: "#a3a3a3", dash: "8 3 2 3" },
] as const;

export function EvalDashboard() {
  const [history, setHistory] = useState<EvalRunSummary[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setHistory(await api.getEvalHistory());
  }

  useEffect(() => {
    load().catch(console.error);
  }, []);

  async function trigger(suite: string) {
    setRunning(true);
    setError(null);
    try {
      const job = await api.runEval(suite);
      const done = await pollJob(job.job_id, undefined, 1500);
      if (done.status === "failed") throw new Error(done.error || "Eval failed");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval failed");
    } finally {
      setRunning(false);
    }
  }

  const retrievalRuns = history.filter((r) => r.suite === "retrieval");
  const latest = retrievalRuns[retrievalRuns.length - 1];
  const chartData = retrievalRuns.map((run) => ({
    label: run.commit_sha.slice(0, 7),
    ...run.metrics,
  }));

  const cards = useMemo(() => {
    if (!latest) return [];
    return [
      ["dense MRR", latest.metrics["dense_mrr"]],
      ["sparse MRR", latest.metrics["sparse_mrr"]],
      ["hybrid MRR", latest.metrics["hybrid_mrr"]],
      ["hybrid+rerank MRR", latest.metrics["hybrid+rerank_mrr"]],
      ["hybrid+rerank hit@5", latest.metrics["hybrid+rerank_hit@5"]],
      ["hybrid+rerank nDCG@10", latest.metrics["hybrid+rerank_ndcg@10"]],
    ].filter(([, v]) => typeof v === "number") as [string, number][];
  }, [latest]);

  return (
    <Page wide>
      <div className="flex items-start justify-between gap-4">
        <PageHeader title="Eval dashboard">
          Retrieval is scored as four ablations on the same questions: dense only, BM25 only, hybrid RRF,
          then hybrid plus the cross-encoder. That is the evidence that each stage does work.
        </PageHeader>
        <div className="flex shrink-0 gap-2">
          <Button variant="secondary" onClick={() => trigger("retrieval")} disabled={running}>
            Run retrieval
          </Button>
          <Button onClick={() => trigger("generation")} disabled={running}>
            Run generation
          </Button>
        </div>
      </div>
      <ErrorText error={error} />

      {cards.length > 0 ? (
        <div className="grid grid-cols-2 gap-px border border-neutral-200 bg-neutral-200 sm:grid-cols-3">
          {cards.map(([key, value]) => (
            <div key={key} className="bg-white p-4">
              <p className="text-xs text-neutral-500">{key}</p>
              <p className="font-serif text-2xl tabular-nums">{value.toFixed(3)}</p>
            </div>
          ))}
        </div>
      ) : (
        <Empty>No retrieval runs yet. Ingest the seed papers, then run retrieval eval.</Empty>
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
              <Line
                key={series.key}
                type="monotone"
                name={series.label}
                dataKey={series.key}
                stroke={series.stroke}
                strokeDasharray={series.dash}
                dot={{ r: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Page>
  );
}
