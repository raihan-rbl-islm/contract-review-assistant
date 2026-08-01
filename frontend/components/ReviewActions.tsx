"use client";

import { useState } from "react";
import type { DecisionType } from "@/lib/types";
import { submitDecision } from "@/lib/api";

interface ReviewActionsProps {
  reviewId: string;
  onDecisionSubmitted?: (decision: DecisionType) => void;
}

export default function ReviewActions({
  reviewId,
  onDecisionSubmitted,
}: ReviewActionsProps) {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<DecisionType | null>(null);
  const [feedbackText, setFeedbackText] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDecision = async (decision: DecisionType) => {
    setSubmitting(true);
    setError(null);
    try {
      await submitDecision(reviewId, {
        decision,
        feedback_text: feedbackText || undefined,
      });
      setSubmitted(decision);
      onDecisionSubmitted?.(decision);
    } catch (e) {
      console.error("Error submitting decision:", e);
      setError("Failed to submit decision. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    const labels: Record<DecisionType, string> = {
      approve: "Approved",
      reject: "Rejected",
      mark_for_review: "Marked for Review",
    };
    return (
      <div className="review-actions submitted">
        <div className={`decision-badge decision-${submitted}`}>
          {submitted === "approve" ? "✓" : submitted === "reject" ? "✗" : "⚑"} {labels[submitted]}
        </div>
        {feedbackText && (
          <p className="feedback-note">Feedback: &ldquo;{feedbackText}&rdquo;</p>
        )}
      </div>
    );
  }

  return (
    <div className="review-actions">
      <div className="action-buttons">
        <button
          className="action-btn approve"
          onClick={() => handleDecision("approve")}
          disabled={submitting}
          type="button"
        >
          Approve
        </button>
        <button
          className="action-btn reject"
          onClick={() => handleDecision("reject")}
          disabled={submitting}
          type="button"
        >
          Reject
        </button>
        <button
          className="action-btn mark-review"
          onClick={() => handleDecision("mark_for_review")}
          disabled={submitting}
          type="button"
        >
          Mark for Review
        </button>
        <button
          className="action-btn feedback-toggle"
          onClick={() => setShowFeedback(!showFeedback)}
          disabled={submitting}
          type="button"
        >
          {showFeedback ? "Hide" : "Add"} Feedback
        </button>
      </div>

      {showFeedback && (
        <div className="feedback-input-container">
          <input
            type="text"
            className="feedback-input"
            placeholder="Add your feedback here..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
          />
        </div>
      )}

      {error && <p className="error-text">{error}</p>}

      <p className="human-review-notice">
        Human review required — this is not legal advice.
      </p>
    </div>
  );
}
