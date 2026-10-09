import { Link } from "react-router-dom";
import { Page } from "../components/ui";

const FIGURE = [
  { k: "01", name: "Parse", detail: "Sections, hyphen repair, sentence windows" },
  { k: "02", name: "Index", detail: "Arctic Embed XS and BM25 in one collection" },
  { k: "03", name: "Fuse", detail: "Reciprocal rank fusion inside Qdrant" },
  { k: "04", name: "Rerank", detail: "MiniLM cross-encoder, when memory allows" },
  { k: "05", name: "Answer", detail: "Cited prose, or the passages themselves" },
];

const WORK = [
  {
    title: "Hybrid retrieval",
    body: "A 384-dimensional int8 encoder and BM25 are fused with reciprocal rank fusion. MiniLM reranks the fused list when it is loaded. The evaluation page reports dense, sparse, hybrid, and hybrid plus rerank on the same questions.",
  },
  {
    title: "Citation integrity",
    body: "For an in-text citation, the attributed claim is extracted and checked against a passage from the cited paper, if that paper is in the library. The verdict is supported, partial, unsupported, contradicted, or unresolved.",
  },
  {
    title: "Abstention",
    body: "Each answer carries a score from retrieval margin, reranker confidence, citation pass rate, and self-consistency. Below the threshold the answer is marked abstained.",
  },
];

export function Home() {
  return (
    <Page>
      <section>
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-neutral-500">PaperMind</p>
        <h1 className="max-w-2xl font-serif text-4xl leading-[1.15] tracking-tight text-neutral-950 sm:text-[2.75rem]">
          Retrieval for papers, with a score that can refuse.
        </h1>
        <p className="mt-6 max-w-2xl text-[15px] leading-7 text-neutral-700">
          Search a library with a local dense encoder and BM25. Ask a question and read the passages it
          used. When a language model is available, the answer is written from those passages and the
          citations are checked. Otherwise the answer is the passages, quoted.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/search"
            className="border border-neutral-950 bg-neutral-950 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Library
          </Link>
          <Link
            to="/chat"
            className="border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-950 hover:border-neutral-950"
          >
            Ask
          </Link>
          <Link
            to="/eval"
            className="border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-950 hover:border-neutral-950"
          >
            Evaluation
          </Link>
        </div>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">Path of a question</h2>
        <ol className="mt-6 border-t border-neutral-950">
          {FIGURE.map((step) => (
            <li key={step.k} className="grid grid-cols-[3rem_7rem_1fr] gap-4 border-b border-neutral-200 py-4 text-sm">
              <span className="font-serif text-neutral-400">{step.k}</span>
              <span className="font-medium text-neutral-950">{step.name}</span>
              <span className="text-neutral-600">{step.detail}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="grid gap-px border border-neutral-200 bg-neutral-200 sm:grid-cols-3">
        {[
          ["384-d", "Arctic Embed XS, int8"],
          ["RRF", "Dense and BM25"],
          ["1.00", "Hybrid MRR, seed set"],
        ].map(([value, label]) => (
          <div key={label} className="bg-white px-5 py-5">
            <p className="font-serif text-3xl tracking-tight text-neutral-950">{value}</p>
            <p className="mt-1 text-xs text-neutral-500">{label}</p>
          </div>
        ))}
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">What is measured</h2>
        <div className="mt-6 grid gap-8 sm:grid-cols-3">
          {WORK.map((item) => (
            <div key={item.title}>
              <h3 className="font-serif text-lg text-neutral-950">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-neutral-600">{item.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-serif text-2xl text-neutral-950">In the library</h2>
        <div className="mt-6 grid border border-neutral-200 sm:grid-cols-2">
          {[
            { to: "/search", label: "Library", desc: "arXiv and PDF ingest" },
            { to: "/chat", label: "Questions", desc: "Passages, citations, trust" },
            { to: "/integrity", label: "Integrity", desc: "Does the citation hold" },
            { to: "/graph", label: "Graph", desc: "Entities and citation edges" },
            { to: "/research", label: "Research", desc: "A question across papers" },
            { to: "/eval", label: "Evaluation", desc: "Ablations on one question set" },
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="flex items-baseline justify-between gap-4 border-b border-neutral-200 px-4 py-4 last:border-b-0 hover:bg-neutral-50 sm:[&:nth-last-child(-n+2)]:border-b-0 sm:odd:border-r"
            >
              <span className="font-medium text-neutral-950">{item.label}</span>
              <span className="text-sm text-neutral-500">{item.desc}</span>
            </Link>
          ))}
        </div>
      </section>
    </Page>
  );
}
