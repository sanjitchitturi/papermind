import type { Source } from "../api/client";

export function SourcePanel({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return <p className="text-sm text-neutral-500">No sources were used for this answer.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-serif text-sm font-semibold text-neutral-950">Sources</h3>
      {sources.map((source) => (
        <details key={source.index} className="border border-neutral-200">
          <summary className="cursor-pointer px-3 py-2 text-sm text-neutral-800">
            <span className="font-medium text-neutral-950">[{source.index}]</span> {source.paper_title}
            <span className="ml-2 text-xs text-neutral-500">
              {source.section} · p.{source.page}
            </span>
          </summary>
          <p className="border-t border-neutral-200 px-3 py-2 text-sm leading-relaxed text-neutral-700">{source.text}</p>
        </details>
      ))}
    </div>
  );
}
