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

// Collapsed by default. This is meant to be the "look, the agent is
// actually reasoning" moment in a demo, not something that clutters the
// page on every page load.
export function ReasoningTrace({ trace }: Props) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded border border-gray-700 bg-gray-900">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-3 py-2 text-left text-sm font-semibold text-gray-300"
      >
        {expanded ? "Hide" : "Show"} reasoning trace ({trace.length} steps)
      </button>
      {expanded && (
        <ol className="flex flex-col gap-2 border-t border-gray-800 p-3">
          {trace.map((step, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium text-gray-400">{KIND_LABELS[step.kind] ?? step.kind}:</span>{" "}
              <span className="text-gray-200">{step.detail}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
