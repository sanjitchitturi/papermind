import { useState } from "react";
import { api } from "../api/client";

interface Props {
  answerId: string;
}

export function FeedbackButtons({ answerId }: Props) {
  const [submitted, setSubmitted] = useState<"up" | "down" | null>(null);

  async function submit(rating: 1 | -1) {
    try {
      await api.sendFeedback(answerId, rating);
      setSubmitted(rating === 1 ? "up" : "down");
    } catch (err) {
      console.error("Failed to submit feedback", err);
    }
  }

  if (submitted) {
    return <p className="text-xs text-neutral-500">Thanks for the feedback.</p>;
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-neutral-500">Was this answer helpful?</span>
      <button onClick={() => submit(1)} className="text-xs text-neutral-700 underline hover:text-neutral-950">
        Helpful
      </button>
      <button onClick={() => submit(-1)} className="text-xs text-neutral-700 underline hover:text-neutral-950">
        Not helpful
      </button>
    </div>
  );
}
