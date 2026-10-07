import { Link } from "react-router-dom";

// Static informational content for the landing page. This is intentionally
// kept as plain data arrays rather than scattered JSX so the page layout
// below stays simple and the copy is easy to edit in one place.

const DIFFERENTIATORS = [
  {
    title: "Citation Integrity Engine",
    body: "Most tools that let you chat with a PDF trust the paper's own citations at face value. PaperMind doesn't. For every in-text citation, it extracts the specific claim being made about the cited work, retrieves the actual passage from that work, and has an LLM judge whether the claim is supported, overstated, or contradicted. It also scans across the whole ingested corpus for papers that make contradictory claims about the same topic.",
  },
  {
    title: "Agentic Research Mode",
    body: "A broad question like \"how do these three papers compare on evaluation methodology\" cannot be answered by a single retrieval call. Research Mode decomposes the question into sub-questions, retrieves evidence for each one across multiple papers, self-critiques the draft answer for gaps in coverage, and synthesizes a narrative review plus an auto-generated comparison table. The reasoning trace is shown in the UI rather than hidden.",
  },
  {
    title: "Calibrated Trust Score",
    body: "Every answer ships with a 0 to 100 score built from retrieval margin, reranker confidence, citation verification pass rate, and self-consistency across repeated generations. Below a configurable threshold, the system says it is not confident and abstains instead of answering fluently but wrong.",
  },
];

const PIPELINE_STEPS = [
  { label: "Ingest", detail: "Parse PDF sections, chunk within sections, resolve bibliography to arXiv IDs" },
  { label: "Index", detail: "Dense + sparse embeddings stored in Qdrant for hybrid retrieval" },
  { label: "Retrieve", detail: "Query rewriting, hybrid search with RRF fusion, LLM reranking" },
  { label: "Generate", detail: "Citation-grounded answer with inline source attribution" },
  { label: "Verify", detail: "Citation integrity check, trust scoring, abstention if below threshold" },
];

const STACK = [
  "FastAPI", "SQLModel", "Postgres", "Qdrant", "OpenAI API",
  "React", "TypeScript", "Vite", "Tailwind CSS",
];

export function Home() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-16 px-6 py-16">
      {/* Hero */}
      <section>
        <h1 className="font-serif text-4xl leading-tight text-neutral-950">
          A research paper assistant that checks its own work.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-neutral-700">
          PaperMind is a retrieval-augmented system for reading and questioning academic papers. It does
          the usual thing, chunk a PDF, embed it, answer questions with citations, and then builds three
          things on top that most "chat with your PDF" tools skip: it verifies that citations actually
          say what papers claim they say, it can research a question across multiple papers at once, and
          it knows when to say it does not know.
        </p>
        <div className="mt-8 flex gap-3">
          <Link
            to="/search"
            className="border border-neutral-950 bg-neutral-950 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Start searching papers
          </Link>
          <a
            href="https://github.com"
            className="border border-neutral-300 px-5 py-2.5 text-sm font-medium text-neutral-950 hover:border-neutral-950"
          >
            View source
          </a>
        </div>
      </section>

      {/* Why this exists */}
      <section>
        <h2 className="font-serif text-2xl text-neutral-950">Why this exists</h2>
        <p className="mt-4 leading-relaxed text-neutral-700">
          Most RAG-for-papers projects stop at chunking, embedding, and answering with citations. That is
          necessary, but a dozen existing tools already do it. PaperMind keeps that core and adds three
          capabilities that address a real failure mode of LLM-based paper assistants: they will cite a
          source confidently even when the source does not actually back up the claim, and they will
          answer confidently even when the retrieved evidence is thin.
        </p>
      </section>

      {/* Differentiators */}
      <section>
        <h2 className="font-serif text-2xl text-neutral-950">What makes it different</h2>
        <div className="mt-6 flex flex-col gap-6">
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

      {/* Pipeline */}
      <section>
        <h2 className="font-serif text-2xl text-neutral-950">How a question gets answered</h2>
        <div className="mt-6 flex flex-col">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={step.label} className="flex gap-4 border-t border-neutral-200 py-4 first:border-t-0">
              <span className="w-6 shrink-0 font-serif text-sm text-neutral-400">{i + 1}</span>
              <span className="w-24 shrink-0 font-medium text-neutral-950">{step.label}</span>
              <span className="text-neutral-700">{step.detail}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Where to go */}
      <section>
        <h2 className="font-serif text-2xl text-neutral-950">Explore the system</h2>
        <div className="mt-6 grid grid-cols-2 gap-px border border-neutral-200 bg-neutral-200 sm:grid-cols-3">
          {[
            { to: "/search", label: "Search", desc: "Find and ingest papers from arXiv or upload a PDF" },
            { to: "/chat", label: "Chat", desc: "Ask questions and see trust-scored, cited answers" },
            { to: "/integrity", label: "Citation Integrity", desc: "See which citations hold up and which don't" },
            { to: "/graph", label: "Knowledge Graph", desc: "Browse extracted entities and relations" },
            { to: "/research", label: "Research Mode", desc: "Compare multiple papers with a visible reasoning trace" },
            { to: "/eval", label: "Eval Dashboard", desc: "Retrieval and citation metrics over time" },
          ].map((item) => (
            <Link key={item.to} to={item.to} className="flex flex-col gap-1 bg-white p-5 hover:bg-neutral-50">
              <span className="font-medium text-neutral-950">{item.label}</span>
              <span className="text-sm text-neutral-500">{item.desc}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Stack */}
      <section className="border-t border-neutral-200 pt-8">
        <h2 className="font-serif text-lg text-neutral-950">Built with</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {STACK.map((item) => (
            <span key={item} className="border border-neutral-300 px-3 py-1 text-xs text-neutral-700">
              {item}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
