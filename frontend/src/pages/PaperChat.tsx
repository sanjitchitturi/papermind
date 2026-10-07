import { useState } from "react";
import { api, type ChatResponse } from "../api/client";
import { FeedbackButtons } from "../components/FeedbackButtons";
import { SourcePanel } from "../components/SourcePanel";
import { TrustScoreBadge } from "../components/TrustScoreBadge";

interface Turn {
  question: string;
  response: ChatResponse;
}

export function PaperChat() {
  const [paperId, setPaperId] = useState("");
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const response = await api.chat(question, paperId.trim() || undefined);
      setTurns((prev) => [...prev, { question, response }]);
      setQuestion("");
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-12">
      <div className="flex items-center gap-2">
        <input
          value={paperId}
          onChange={(e) => setPaperId(e.target.value)}
          placeholder="Paper id (leave empty to chat with the whole library)"
          className="flex-1 border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 placeholder:text-neutral-400"
        />
      </div>

      <div className="flex flex-col gap-8">
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-3 border-t border-neutral-200 pt-6">
            <p className="font-serif text-lg text-neutral-950">{turn.question}</p>
            <p className="whitespace-pre-wrap text-neutral-800">{turn.response.answer}</p>
            <TrustScoreBadge
              score={turn.response.trust_score}
              explanation={turn.response.trust_explanation}
              abstained={turn.response.abstained}
            />
            <SourcePanel sources={turn.response.sources} />
            <FeedbackButtons answerId={turn.response.answer_id} />
          </div>
        ))}
      </div>

      <div className="sticky bottom-4 flex gap-2 border border-neutral-300 bg-white p-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask a question about the paper or the whole library..."
          className="flex-1 bg-transparent px-2 py-2 text-sm text-neutral-950 outline-none placeholder:text-neutral-400"
        />
        <button
          onClick={ask}
          disabled={loading}
          className="border border-neutral-950 bg-neutral-950 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-40"
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>
    </div>
  );
}
