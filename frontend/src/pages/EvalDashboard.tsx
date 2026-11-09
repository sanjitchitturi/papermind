import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, pollJob, type EvalRunSummary } from "../api/client";
import { Button, Empty, ErrorText, Page, PageHeader } from "../components/ui";

const SERIES = [
  { key: "bm25_mrr", label: "BM25 MRR", stroke: "#234e39", dash: undefined },
  { key: "bm25_hit@5", label: "BM25 hit@5", stroke: "#718d62", dash: "6 3" },
  {
    key: "bm25_ndcg@10",
    label: "BM25 nDCG@10",
    stroke: "#a1ab94",
    dash: "2 2",
  },
] as const;

export function EvalDashboard() {
  const [history, setHistory] = useState<EvalRunSummary[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setHistory(await api.getEvalHistory());
  }

  useEffect(() => {
    load().catch((err) =>
      setError(
        err instanceof Error
          ? err.message
          : "Could not load evaluation history.",
      ),
    );
  }, []);

  async function trigger(suite: string) {
    setRunning(true);
    setError(null);
    try {
      const job = await api.runEval(suite);
      const done = await pollJob(job.job_id, undefined, 1500);
      if (done.status === "failed")
        throw new Error(done.error || "Eval failed");
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
      ["BM25 MRR", latest.metrics["bm25_mrr"]],
      ["BM25 hit@5", latest.metrics["bm25_hit@5"]],
      ["BM25 nDCG@10", latest.metrics["bm25_ndcg@10"]],
    ].filter(([, v]) => typeof v === "number") as [string, number][];
  }, [latest]);

  return (
    <Page wide>
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row">
        <PageHeader title="Evaluation">
          Measure local keyword retrieval against the bundled question set.
          Results depend on which benchmark papers are in your library; sample
          notes are not a benchmark. These scores do not measure factual
          correctness.
        </PageHeader>
        <div className="flex shrink-0 gap-2">
          <Button
            variant="secondary"
            onClick={() => trigger("retrieval")}
            disabled={running}
          >
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
              <p className="font-serif text-2xl tabular-nums">
                {value.toFixed(3)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <Empty>
          No retrieval runs yet. Add the benchmark papers listed in the
          documentation, then run retrieval evaluation.
        </Empty>
      )}

      {chartData.length > 0 && (
        <div className="h-80 rounded-lg border border-neutral-200 bg-white p-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="2 2" stroke="#e5e5e5" />
              <XAxis dataKey="label" stroke="#a3a3a3" fontSize={11} />
              <YAxis domain={[0, 1]} stroke="#a3a3a3" fontSize={11} />
              <Tooltip
                contentStyle={{
                  background: "#ffffff",
                  border: "1px solid #d4d4d4",
                  color: "#0a0a0a",
                }}
              />
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
      )}
      {history
        .filter((run) => run.suite === "generation")
        .map((run) => (
          <section
            key={run.id}
            className="rounded-lg border border-neutral-200 bg-white p-4"
          >
            <h2 className="font-serif text-lg">Answer evaluation</h2>
            <p className="mt-1 text-xs text-neutral-500">
              Keyword overlap and citation-format checks; not a factual accuracy
              assessment.
            </p>
            <dl className="mt-3 grid gap-2 text-sm">
              {Object.entries(run.metrics).map(([name, value]) => (
                <div key={name} className="flex justify-between gap-4">
                  <dt>{name.replace(/_/g, " ")}</dt>
                  <dd className="tabular-nums">
                    {Number.isInteger(value) ? value : value.toFixed(3)}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
    </Page>
  );
}
