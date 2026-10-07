interface Props {
  score: number;
  explanation: string;
  abstained: boolean;
}

// Five segments, filled left-to-right in proportion to the score. Darker /
// fuller reads as "more trustworthy" without needing color to say so.
const SEGMENT_COUNT = 5;

export function TrustScoreBadge({ score, explanation, abstained }: Props) {
  const filled = Math.round((score / 100) * SEGMENT_COUNT);

  return (
    <div className="inline-flex flex-col gap-1.5 rounded border border-neutral-300 px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-0.5" aria-hidden="true">
          {Array.from({ length: SEGMENT_COUNT }).map((_, i) => (
            <span
              key={i}
              className={`h-2.5 w-2.5 ${i < filled ? "bg-neutral-950" : "border border-neutral-300 bg-transparent"}`}
            />
          ))}
        </div>
        <span className="font-medium text-neutral-950">Trust score: {score}/100</span>
        {abstained && (
          <span className="rounded border border-neutral-950 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-950">
            Abstained
          </span>
        )}
      </div>
      <div className="text-xs text-neutral-600">{explanation}</div>
    </div>
  );
}
