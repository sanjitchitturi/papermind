import type { Source } from "../api/client";

interface Props {
  sources: Source[];
}

export function SourcePanel({ sources }: Props) {
  if (sources.length === 0) {
    return <p className="text-sm text-gray-500">No sources were used for this answer.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-gray-300">Sources</h3>
      {sources.map((source) => (
        <div key={source.index} className="rounded border border-gray-700 bg-gray-900 p-3 text-sm">
          <div className="mb-1 flex items-center justify-between text-xs text-gray-400">
            <span>
              [{source.index}] {source.paper_title}
            </span>
            <span className="rounded bg-gray-800 px-2 py-0.5">{source.section}</span>
          </div>
          <p className="text-gray-200">{source.text}</p>
        </div>
      ))}
    </div>
  );
}
