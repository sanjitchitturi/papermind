import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type ChatResponse, type Paper } from "../api/client";
import { FeedbackButtons } from "../components/FeedbackButtons";
import { SourcePanel } from "../components/SourcePanel";
import { TrustScoreBadge } from "../components/TrustScoreBadge";
import {
  Button,
  ErrorText,
  Page,
  PageHeader,
  Select,
  TextArea,
} from "../components/ui";

interface Turn {
  question: string;
  response: ChatResponse;
}

const SUGGESTIONS = [
  "What problem does this paper claim to solve?",
  "How does the method differ from prior work?",
  "What datasets and metrics are reported?",
];

export function PaperChat() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [params] = useSearchParams();
  const [paperId, setPaperId] = useState(params.get("paper") ?? "");
  const pending = useRef(false);
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listPapers()
      .then(setPapers)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Could not load the library.",
        ),
      );
  }, []);

  async function ask(text = question) {
    if (!text.trim() || pending.current) return;
    pending.current = true;
    setLoading(true);
    setError(null);
    try {
      const response = await api.chat(text, paperId || undefined);
      setTurns((prev) => [...prev, { question: text, response }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      pending.current = false;
      setLoading(false);
    }
  }

  return (
    <Page>
      <PageHeader title="Questions">
        One paper, or the whole library. The passages are retrieved locally. A
        language model writes the answer when it responds. Otherwise the answer
        is those passages, quoted.
      </PageHeader>

      <Select
        value={paperId}
        onChange={(e) => setPaperId(e.target.value)}
        aria-label="Paper scope"
      >
        <option value="">Entire library ({papers.length} papers)</option>
        {papers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title}
          </option>
        ))}
      </Select>

      <ErrorText error={error} />

      {papers.length === 0 && (
        <p className="rounded-lg border border-neutral-200 p-4 text-sm text-neutral-600">
          Start with{" "}
          <Link to="/search" className="underline">
            a paper in your library
          </Link>
          , or{" "}
          <Link to="/" className="underline">
            try sample notes
          </Link>
          .
        </p>
      )}

      {turns.length === 0 && !loading && papers.length > 0 && (
        <div className="border border-neutral-200 p-6">
          <p className="text-sm text-neutral-600">
            Try a question, or start from one of these:
          </p>
          <div className="mt-4 flex flex-col gap-2">
            {SUGGESTIONS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => ask(item)}
                className="border border-neutral-200 px-3 py-2 text-left text-sm text-neutral-800 hover:border-neutral-950"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-10">
        {turns.map((turn, i) => (
          <article
            key={i}
            className="flex flex-col gap-3 border-t border-neutral-200 pt-6"
          >
            <p className="font-serif text-lg text-neutral-950">
              {turn.question}
            </p>
            <p className="whitespace-pre-wrap leading-relaxed text-neutral-800">
              {turn.response.answer}
            </p>
            <TrustScoreBadge
              score={turn.response.trust_score}
              explanation={turn.response.trust_explanation}
              abstained={turn.response.abstained}
              signals={turn.response.trust_signals}
              mode={turn.response.mode}
              latencyMs={turn.response.latency_ms}
            />
            <SourcePanel sources={turn.response.sources} />
            <FeedbackButtons answerId={turn.response.answer_id} />
          </article>
        ))}
        {loading && (
          <p role="status" className="text-sm text-neutral-500">
            Retrieving and ranking passages...
          </p>
        )}
      </div>

      <div className="sticky bottom-4 flex items-end gap-2 border border-neutral-300 bg-white p-2">
        <TextArea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              void ask();
            }
          }}
          placeholder="Ask about the paper or the library..."
          aria-label="Question"
        />
        <Button onClick={() => ask()} disabled={loading || !question.trim()}>
          {loading ? "Thinking..." : "Ask"}
        </Button>
      </div>
    </Page>
  );
}
