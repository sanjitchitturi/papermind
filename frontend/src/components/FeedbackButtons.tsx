import { useState } from "react";
import { api } from "../api/client";

interface Props {
  answerId: string;
}

// Thumbs up/down feeds the feedback loop described in the plan: a
// thumbs-down on a high-trust answer gets flagged server-side as a
// candidate regression case for the eval dataset.
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
    return <p className="text-xs text-gray-500">Thanks for the feedback.</p>;
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500">Was this answer helpful?</span>
      <button
        onClick={() => submit(1)}
        className="rounded border border-gray-700 px-2 py-1 text-xs hover:bg-gray-800"
      >
        Yes
      </button>
      <button
        onClick={() => submit(-1)}
        className="rounded border border-gray-700 px-2 py-1 text-xs hover:bg-gray-800"
      >
        No
      </button>
    </div>
  );
}
