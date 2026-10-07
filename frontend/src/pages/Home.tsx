import { Link } from "react-router-dom";
import { Page } from "../components/ui";

const STATS = [
  { value: "384-d", label: "Arctic Embed XS, int8 ONNX" },
  { value: "RRF", label: "Dense + BM25 fused in Qdrant" },
  { value: "1.00", label: "Hybrid MRR on the seed set" },
  { value: "512 MB", label: "Live API leaves the reranker off" },
];

const DIFFERENTIATORS = [
  {
    title: "Hybrid retrieval, with a measured reranker",
    body: "First-stage search fuses a local dense encoder (Snowflake Arctic Embed XS, int8 ONNX) with BM25 sparse vectors inside Qdrant via reciprocal rank fusion. A MiniLM cross-encoder can rerank the fused candidates. The live API leaves that second model off so the process fits in 512 MB. Locally, and on a larger box, the eval dashboard reports dense, sparse, hybrid, and hybrid+rerank separately.",
  },
  {
    title: "Citation Integrity Engine",
    body: "Most chat-with-PDF tools trust a paper's citations at face value. For every in-text citation, PaperMind extracts the claim being attributed to the cited work, retrieves a passage from that work if it is in the library, and judges whether the claim is supported, overstated, or contradicted. Unresolvable citations are recorded as unresolved rather than guessed.",
  },
  {
    title: "Calibrated trust, with abstention",
    body: "Every answer carries a 0-100 score from retrieval margin, reranker confidence, citation pass rate, and self-consistency. Below a threshold the system says it is not confident instead of answering fluently but wrong. The score breakdown is visible in the UI.",
  },
];

const PIPELINE = [
  { label: "Parse", detail: "Section detection, header stripping, hyphen repair, sentence-aware chunks" },
  { label: "Index", detail: "Local dense + BM25 sparse vectors in Qdrant, IDF applied server-side" },
  { label: "Retrieve", detail: "RRF fusion. Cross-encoder rerank when memory allows" },
  { label: "Answer", detail: "Cited generation when the LLM call succeeds, quoted passages otherwise" },
  { label: "Verify", detail: "Citation checks, trust scoring, abstention below threshold" },
];

const MODELS = [
  { role: "Dense", name: "snowflake-arctic-embed-xs", note: "23 MB int8, query prefix, cosine ~0.998 vs fp32" },
  { role: "Sparse", name: "Qdrant/bm25", note: "Term frequencies in the collection; IDF at query time" },
  { role: "Rerank", name: "ms-marco-MiniLM-L-6-v2", note: "Optional. Off on the 512 MB deploy" },
  { role: "Generate", name: "gpt-4o-mini or compatible", note: "Quoted passages if the call fails or no key is set" },
];

export function Home() {
  return (
    <Page>
      <section>
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-500">
          Research retrieval
        </p>
        <h1 className="max-w-2xl font-serif text-4xl leading-[1.15] tracking-tight text-neutral-950 sm:text-5xl">
          A paper assistant that checks its own work.
        </h1>
        <p className="mt-6 max-w-2xl text-base leading-relaxed text-neutral-700">
          PaperMind is a retrieval system for academic papers. Dense retrieval and BM25 run on local
          ONNX models. The MiniLM reranker is in the codebase and measured locally; the free API leaves
          it off. Chat falls back to quoted passages if generation is unavailable. Integrity and research
          mode need a funded OpenAI-compatible key.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/search"
            className="border border-neutral-950 bg-neutral-950 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Open the library
          </Link>
          <Link
            to="/eval"
            className="border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-950 hover:border-neutral-950"
          >
            See the evals
          </Link>
          <a
            href="https://github.com/sanjitchitturi/papermind"
            className="border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-950 hover:border-neutral-950"
          >
            Source on GitHub
          </a>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-px border border-neutral-200 bg-neutral-200 sm:grid-cols-4">
        {STATS.map((stat) => (
          <div key={stat.label} className="bg-white px-4 py-5">
            <p className="font-serif text-2xl tracking-tight text-neutral-950">{stat.value}</p>
            <p className="mt-1 text-xs leading-snug text-neutral-500">{stat.label}</p>
          </div>
        ))}
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">What is actually different</h2>
        <div className="mt-6 flex flex-col gap-4">
          {DIFFERENTIATORS.map((item, i) => (
            <div key={item.title} className="border border-neutral-200 p-6">
              <div className="flex items-baseline gap-3">
                <span className="font-serif text-sm text-neutral-400">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="font-serif text-lg text-neutral-950">{item.title}</h3>
              </div>
              <p className="mt-3 leading-relaxed text-neutral-700">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">How a question is answered</h2>
        <div className="mt-6 flex flex-col">
          {PIPELINE.map((step, i) => (
            <div key={step.label} className="flex gap-4 border-t border-neutral-200 py-4 first:border-t-0">
              <span className="w-6 shrink-0 font-serif text-sm text-neutral-400">{i + 1}</span>
              <span className="w-24 shrink-0 font-medium text-neutral-950">{step.label}</span>
              <span className="text-neutral-700">{step.detail}</span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">Models on the box</h2>
        <p className="mt-2 max-w-2xl text-sm text-neutral-600">
          Chosen so the API, including ONNX sessions, fits on a 512 MB Render instance. Weights are int8.
          Collection names include the embedder and dimension, so a model swap does not mix vector spaces.
        </p>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-neutral-950 text-left text-neutral-500">
                <th className="py-2 pr-4 font-medium">Role</th>
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody>
              {MODELS.map((row) => (
                <tr key={row.role} className="border-b border-neutral-200 align-top">
                  <td className="py-3 pr-4 font-medium text-neutral-950">{row.role}</td>
                  <td className="py-3 pr-4 font-mono text-xs text-neutral-700">{row.name}</td>
                  <td className="py-3 text-neutral-600">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">Explore</h2>
        <div className="mt-6 grid grid-cols-2 gap-px border border-neutral-200 bg-neutral-200 sm:grid-cols-3">
          {[
            { to: "/search", label: "Library", desc: "Search arXiv, upload a PDF, browse ingested papers" },
            { to: "/chat", label: "Chat", desc: "Ask questions with sources and a trust breakdown" },
            { to: "/integrity", label: "Integrity", desc: "Check whether citations hold up" },
            { to: "/graph", label: "Graph", desc: "Entities and citation edges across the library" },
            { to: "/research", label: "Research", desc: "Multi-paper review with a visible trace" },
            { to: "/eval", label: "Eval", desc: "Retrieval ablations, not a single vanity number" },
          ].map((item) => (
            <Link key={item.to} to={item.to} className="flex flex-col gap-1 bg-white p-5 hover:bg-neutral-50">
              <span className="font-medium text-neutral-950">{item.label}</span>
              <span className="text-sm text-neutral-500">{item.desc}</span>
            </Link>
          ))}
        </div>
      </section>
    </Page>
  );
}
