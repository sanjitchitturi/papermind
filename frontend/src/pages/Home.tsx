import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button, ErrorText, Page } from "../components/ui";

const TOOLS = [
  {
    to: "/search",
    number: "01",
    title: "Build your library",
    detail:
      "Bring a PDF or find a paper on arXiv. Your research stays in your local workspace.",
  },
  {
    to: "/chat",
    number: "02",
    title: "Ask with evidence",
    detail:
      "Find the passages behind an answer. Read source excerpts before drawing a conclusion.",
  },
  {
    to: "/research",
    number: "03",
    title: "Connect the ideas",
    detail:
      "Explore a question across papers, compare findings, and follow the research trail.",
  },
];

export function Home() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function demo() {
    setLoading(true);
    setError(null);
    try {
      await api.seedDemo();
      window.dispatchEvent(new Event("library-updated"));
      navigate("/search");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load sample notes.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <Page wide>
      <section className="hero-grid">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="status-dot" /> Your local research workspace
          </p>
          <h1 className="hero-title">
            Good questions.
            <br />
            <em>Grounded answers.</em>
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-neutral-600">
            Make sense of the papers you read. Build a library, explore ideas,
            and keep the evidence close.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/search" className="action-link">
              Open your library <span aria-hidden>↗</span>
            </Link>
            <Button variant="secondary" onClick={demo} disabled={loading}>
              {loading ? "Preparing samples…" : "Try sample notes"}
            </Button>
          </div>
          <p className="mt-4 text-xs leading-5 text-neutral-500">
            No account or API key needed. Samples are illustrative notes, not
            published papers.
          </p>
          <div className="mt-4">
            <ErrorText error={error} />
          </div>
        </div>
        <div
          className="research-preview"
          aria-label="Illustration of a research note"
        >
          <div className="flex items-center justify-between border-b border-[#d9dfd8] pb-4">
            <span className="eyebrow">The reading desk</span>
            <span className="text-xs text-neutral-500">PaperMind / 001</span>
          </div>
          <p className="mt-7 font-serif text-2xl leading-snug text-[#163e32]">
            Every answer starts
            <br />
            with a source.
          </p>
          <div className="note-excerpt">
            <span className="note-marker">[1]</span>
            <div>
              <p className="eyebrow mb-2">Source passage</p>
              <div className="note-line w-full" />
              <div className="note-line w-[92%]" />
              <div className="note-line w-[74%]" />
            </div>
          </div>
          <div className="flex items-center gap-3 border-t border-[#d9dfd8] pt-4 text-xs text-[#4e6659]">
            <span className="status-dot" /> Local retrieval{" "}
            <span className="ml-auto">Evidence first</span>
          </div>
          <span className="preview-tab">A place for curiosity</span>
        </div>
      </section>
      <section className="principles-strip">
        <span>Stored on your machine</span>
        <span>No cloud database</span>
        <span>Source-linked answers</span>
        <span>Optional language model</span>
      </section>
      <section>
        <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow mb-2">From reading to understanding</p>
            <h2 className="font-serif text-3xl">
              A clearer path through the literature.
            </h2>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {TOOLS.map((tool) => (
            <Link key={tool.to} to={tool.to} className="tool-card">
              <span className="text-xs text-[#66806f]">{tool.number} /</span>
              <h3 className="mt-8 font-serif text-xl">
                {tool.title}{" "}
                <span aria-hidden className="float-right text-[#66806f]">
                  ↗
                </span>
              </h3>
              <p className="mt-3 text-sm leading-6 text-neutral-600">
                {tool.detail}
              </p>
            </Link>
          ))}
        </div>
      </section>
      <section className="rounded-xl border border-neutral-200 bg-white p-6 sm:p-8">
        <p className="eyebrow mb-3">Built for careful reading</p>
        <div className="grid gap-6 md:grid-cols-2">
          <h2 className="font-serif text-2xl leading-snug">
            Useful without a model.
            <br />
            More flexible with one.
          </h2>
          <div className="space-y-3 text-sm leading-6 text-neutral-600">
            <p>
              Local keyword retrieval returns relevant excerpts directly.
              Connect an OpenAI-compatible language model to draft cited answers
              and run assisted citation checks.
            </p>
            <p>
              Scores are heuristic signals, not proof of correctness. Always
              inspect the passages and the original paper.
            </p>
            <Link
              to="/eval"
              className="inline-block font-medium text-[#245b45] underline underline-offset-4"
            >
              Explore evaluation →
            </Link>
          </div>
        </div>
      </section>
    </Page>
  );
}
