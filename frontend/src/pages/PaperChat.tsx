import { useEffect, useState } from "react";
import { api, type ChatResponse, type Paper } from "../api/client";
import { FeedbackButtons } from "../components/FeedbackButtons";
import { SourcePanel } from "../components/SourcePanel";
import { TrustScoreBadge } from "../components/TrustScoreBadge";
import { Button, ErrorText, Input, Page, PageHeader } from "../components/ui";

interface Turn {
  question: string;
  response: ChatResponse;
}

export function PaperChat() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [paperId, setPaperId] = useState("");
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listPapers().then(setPapers).catch(() => setPapers([]));
  }, []);

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.chat(question, paperId || undefined);
      setTurns((prev) => [...prev, { question, response }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Page>
      <PageHeader title="Chat">
        Scoped to one paper or the whole library. Retrieval is local. If no LLM key is configured, answers
        are extractive quotes from the top passages rather than generated prose.
      </PageHeader>

      <select
        value={paperId}
        onChange={(e) => setPaperId(e.target.value)}
        className="border border-neutral-300 bg-white px-3 py-2 text-sm"
      >
        <option value="">Entire library</option>
        {papers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.title}
          </option>
        ))}
      </select>

      <ErrorText error={error} />

      <div className="flex flex-col gap-10">
        {turns.map((turn, i) => (
          <article key={i} className="flex flex-col gap-3 border-t border-neutral-200 pt-6">
            <p className="font-serif text-lg text-neutral-950">{turn.question}</p>
            <p className="whitespace-pre-wrap leading-relaxed text-neutral-800">{turn.response.answer}</p>
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
      </div>

      <div className="sticky bottom-4 flex gap-2 border border-neutral-300 bg-white p-2">
        <Input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask about the paper or the library..."
          className="border-0"
        />
        <Button onClick={ask} disabled={loading}>
          {loading ? "Thinking..." : "Ask"}
        </Button>
      </div>
    </Page>
  );
}
