import { useState } from "react";
import { api } from "../api/client";

export function FeedbackButtons({ answerId }: { answerId: string }) {
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(rating: 1 | -1) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api.sendFeedback(answerId, rating);
      setSubmitted(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Feedback was not saved. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  if (submitted)
    return (
      <p role="status" className="text-xs text-neutral-500">
        Feedback saved. Thank you.
      </p>
    );
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="text-neutral-500">Was this answer helpful?</span>
        <button
          type="button"
          disabled={busy}
          onClick={() => submit(1)}
          className="underline disabled:opacity-40"
        >
          Helpful
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => submit(-1)}
          className="underline disabled:opacity-40"
        >
          Not helpful
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-800">
          {error}
        </p>
      )}
    </div>
  );
}
