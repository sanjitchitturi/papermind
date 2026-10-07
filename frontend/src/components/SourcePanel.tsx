import type { Source } from "../api/client";

interface Props {
  sources: Source[];
}

export function SourcePanel({ sources }: Props) {
  if (sources.length === 0) {
    return <p className="text-sm text-neutral-500">No sources were used for this answer.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-serif text-sm font-semibold text-neutral-950">Sources</h3>
      {sources.map((source) => (
        <div key={source.index} className="border border-neutral-200 p-3 text-sm">
          <div className="mb-1 flex items-center justify-between text-xs text-neutral-500">
            <span>
              [{source.index}] {source.paper_title}
            </span>
            <span className="border border-neutral-300 px-2 py-0.5 uppercase tracking-wide text-[10px]">
              {source.section}
            </span>
          </div>
          <p className="text-neutral-800">{source.text}</p>
        </div>
      ))}
    </div>
  );
}
