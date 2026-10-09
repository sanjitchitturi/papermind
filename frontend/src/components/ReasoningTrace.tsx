import { useState } from "react";
import type { TraceStep } from "../api/client";

interface Props {
  trace: TraceStep[];
}

const KIND_LABELS: Record<string, string> = {
  decompose: "Decomposed question",
  retrieve: "Retrieved evidence",
  critique: "Checked coverage",
  synthesize: "Synthesized answer",
};

export function ReasoningTrace({ trace }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-neutral-200">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-3 py-2 text-left text-sm font-medium text-neutral-800"
      >
        {expanded ? "Hide" : "Show"} reasoning trace ({trace.length} steps)
      </button>
      {expanded && (
        <ol className="flex flex-col gap-2 border-t border-neutral-200 p-3">
          {trace.map((step, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium text-neutral-500">{KIND_LABELS[step.kind] ?? step.kind}:</span>{" "}
              <span className="text-neutral-900">{step.detail}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
