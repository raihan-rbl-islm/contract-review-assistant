"use client";

import type { ReviewResponse } from "@/lib/types";
import ReviewActions from "./ReviewActions";

interface NotEnoughInfoStateProps {
  review: ReviewResponse;
}

export default function NotEnoughInfoState({ review }: NotEnoughInfoStateProps) {
  return (
    <div className="evidence-card nei-card">
      {/* Top border instead of left tab — quieter visual per Plan.md §16.4 */}
      <div className="nei-top-border" />

      <div className="evidence-content">
        {/* Header */}
        <div className="evidence-header">
          <div className="evidence-meta">
            <span className="mono-id">{review.contract_id}</span>
            <span className="category-label">{review.clause_type}</span>
          </div>
        </div>

        {/* Central message */}
        <div className="nei-message">
          <p className="nei-text">Not enough information to make a reliable assessment.</p>
          <p className="nei-reason">{review.reason}</p>
        </div>

        {/* Standard reference (grayed, for context) */}
        <div className="evidence-block nei-standard">
          <span className="evidence-label">
            Company Standard — <span className="mono-id">{review.standard_id}</span>
          </span>
          <blockquote className="evidence-quote standard-quote nei-quote">
            <span className="quote-mark">&ldquo;</span>
            {review.standard_text}
            <span className="quote-mark">&rdquo;</span>
          </blockquote>
        </div>

        {/* Actions footer */}
        <div className="evidence-footer">
          <ReviewActions reviewId={review.id} />
        </div>
      </div>
    </div>
  );
}
