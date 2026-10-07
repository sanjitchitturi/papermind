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
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <div className="flex items-center gap-2">
        <input
          value={paperId}
          onChange={(e) => setPaperId(e.target.value)}
          placeholder="Paper id (leave empty to chat with the whole library)"
          className="flex-1 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm"
        />
      </div>

      <div className="flex flex-col gap-6">
        {turns.map((turn, i) => (
          <div key={i} className="flex flex-col gap-3 rounded border border-gray-800 p-4">
            <p className="font-medium text-gray-100">{turn.question}</p>
            <p className="whitespace-pre-wrap text-gray-200">{turn.response.answer}</p>
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

      <div className="sticky bottom-4 flex gap-2 rounded border border-gray-700 bg-gray-900 p-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask a question about the paper or the whole library..."
          className="flex-1 bg-transparent px-2 py-2 text-sm outline-none"
        />
        <button
          onClick={ask}
          disabled={loading}
          className="rounded bg-blue-700 px-4 py-2 text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? "Thinking..." : "Ask"}
        </button>
      </div>
    </div>
  );
}
