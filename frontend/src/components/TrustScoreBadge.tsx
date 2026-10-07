interface Props {
  score: number;
  explanation: string;
  abstained: boolean;
}

// Color bands are intentionally coarse (red/yellow/green) rather than a
// continuous gradient, a quick glance should tell you which bucket an
// answer falls into without having to read the exact number.
function colorForScore(score: number): string {
  if (score < 45) return "bg-red-900 text-red-200 border-red-700";
  if (score < 75) return "bg-yellow-900 text-yellow-200 border-yellow-700";
  return "bg-green-900 text-green-200 border-green-700";
}

export function TrustScoreBadge({ score, explanation, abstained }: Props) {
  return (
    <div className={`inline-flex flex-col gap-1 rounded-md border px-3 py-2 text-sm ${colorForScore(score)}`}>
      <div className="flex items-center gap-2 font-semibold">
        <span>Trust score: {score}/100</span>
        {abstained && <span className="rounded bg-black/30 px-2 py-0.5 text-xs">abstained</span>}
      </div>
      <div className="text-xs opacity-90">{explanation}</div>
    </div>
  );
}
