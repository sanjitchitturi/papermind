import type { TrustSignals } from "../api/client";

interface Props {
  score: number;
  explanation: string;
  abstained: boolean;
  signals?: TrustSignals;
  mode?: string;
  latencyMs?: number;
}

const SEGMENT_COUNT = 5;

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function TrustScoreBadge({ score, explanation, abstained, signals, mode, latencyMs }: Props) {
  const filled = Math.round((score / 100) * SEGMENT_COUNT);

  return (
    <div className="flex flex-col gap-2 border border-neutral-200 px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-0.5" aria-hidden="true">
          {Array.from({ length: SEGMENT_COUNT }).map((_, i) => (
            <span
              key={i}
              className={`h-2.5 w-2.5 ${i < filled ? "bg-neutral-950" : "border border-neutral-300 bg-transparent"}`}
            />
          ))}
        </div>
        <span className="font-medium text-neutral-950">Trust {score}/100</span>
        {abstained && (
          <span className="border border-neutral-950 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
            Abstained
          </span>
        )}
        {mode && <span className="text-[10px] uppercase tracking-wide text-neutral-500">{mode}</span>}
        {latencyMs !== undefined && <span className="text-[10px] text-neutral-400">{latencyMs} ms</span>}
      </div>
      <p className="text-xs text-neutral-600">{explanation}</p>
      {signals && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-neutral-500 sm:grid-cols-4">
          <div>
            <dt>Margin</dt>
            <dd className="font-medium text-neutral-800">{pct(signals.retrieval_margin)}</dd>
          </div>
          <div>
            <dt>Rerank</dt>
            <dd className="font-medium text-neutral-800">{pct(signals.rerank_confidence)}</dd>
          </div>
          <div>
            <dt>Citations</dt>
            <dd className="font-medium text-neutral-800">{pct(signals.citation_pass_rate)}</dd>
          </div>
          <div>
            <dt>Consistency</dt>
            <dd className="font-medium text-neutral-800">{pct(signals.self_consistency)}</dd>
          </div>
        </dl>
      )}
    </div>
  );
}
