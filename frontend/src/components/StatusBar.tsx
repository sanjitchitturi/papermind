import { useEffect, useState } from "react";
import { api, type Capabilities } from "../api/client";

export function StatusBar() {
  const [caps, setCaps] = useState<Capabilities | null>(null);

  useEffect(() => {
    api.capabilities().then(setCaps).catch(() => setCaps(null));
  }, []);

  if (!caps) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-neutral-200 bg-neutral-50 px-6 py-1.5 text-[11px] text-neutral-500">
      <span>
        {caps.embedding_model} · {caps.embedding_dim}d
      </span>
      <span>{caps.reranker_model}</span>
      <span>{caps.llm_configured ? `LLM ${caps.llm_model}` : "Extractive mode (no LLM key)"}</span>
      <span className="ml-auto">
        {caps.papers}/{caps.max_papers} papers · {caps.chunks_indexed} chunks
      </span>
    </div>
  );
}
