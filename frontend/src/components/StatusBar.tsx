import { useEffect, useState } from "react";
import { api, type Capabilities, type Health } from "../api/client";

export function StatusBar() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    let active = true;
    async function refresh() {
      const [c, h] = await Promise.allSettled([
        api.capabilities(),
        api.health(),
      ]);
      if (!active) return;
      setCaps(c.status === "fulfilled" ? c.value : null);
      setHealth(h.status === "fulfilled" ? h.value : null);
      setChecked(true);
    }
    void refresh();
    window.addEventListener("library-updated", refresh);
    return () => {
      active = false;
      window.removeEventListener("library-updated", refresh);
    };
  }, []);
  const live = health?.status === "ok";
  return (
    <div className="border-b border-neutral-200 bg-[#eef2ed]">
      <div
        role="status"
        className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-1 px-6 py-2 text-[11px] text-[#52675b]"
      >
        <span className="inline-flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${live ? "bg-[#3a7354]" : "bg-neutral-400"}`}
            aria-hidden
          />
          {live
            ? "Workspace ready"
            : !checked
              ? "Connecting to workspace…"
              : health
                ? "Workspace needs attention"
                : "API unavailable · start the local server"}
        </span>
        {caps && (
          <>
            <span>Local keyword retrieval</span>
            <span>
              {caps.llm_configured
                ? `Model: ${caps.llm_model}`
                : "Extractive answers"}
            </span>
            <span className="md:ml-auto">
              {caps.papers} papers · {caps.chunks_indexed} passages
            </span>
          </>
        )}
      </div>
    </div>
  );
}
