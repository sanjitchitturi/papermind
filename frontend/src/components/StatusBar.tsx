import { useEffect, useState } from "react";
import { api, type Capabilities, type Health } from "../api/client";

function rerankLabel(model: string) {
  if (!model || model === "none" || model === "off" || model === "disabled") return "Reranker off";
  return model;
}

export function StatusBar() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => setCaps(null));
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  if (!caps && !health) return null;

  const live = health?.postgres && health?.qdrant;

  return (
    <div className="border-b border-neutral-200 bg-neutral-50">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 px-6 py-1.5 text-[11px] tabular-nums text-neutral-500">
        <span className="inline-flex items-center gap-1.5">
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${live ? "bg-neutral-950" : "bg-neutral-300"}`}
            aria-hidden
          />
          {live ? "API live" : health ? "API degraded" : "API unreachable"}
        </span>
        {caps && (
          <>
            <span>
              {caps.embedding_model} · {caps.embedding_dim}d
            </span>
            <span>{rerankLabel(caps.reranker_model)}</span>
            <span>{caps.llm_configured ? `LLM ${caps.llm_model}` : "Extractive mode"}</span>
            <span className="md:ml-auto">
              {caps.papers}/{caps.max_papers} papers · {caps.chunks_indexed} chunks
            </span>
          </>
        )}
      </div>
    </div>
  );
}
