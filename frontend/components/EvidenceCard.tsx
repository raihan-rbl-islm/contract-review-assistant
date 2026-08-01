"use client";

import type { ReviewResponse } from "@/lib/types";
import RiskBadge from "./RiskBadge";
import ReviewActions from "./ReviewActions";

interface EvidenceCardProps {
  review: ReviewResponse;
}

export default function EvidenceCard({ review }: EvidenceCardProps) {
  const riskColorClass =
    review.risk_level === "Low Risk"
      ? "tab-low"
      : review.risk_level === "Medium Risk"
        ? "tab-medium"
        : review.risk_level === "High Risk"
          ? "tab-high"
          : "tab-unknown";

  return (
    <div className={`evidence-card ${riskColorClass}`}>
      {/* Left color tab strip */}
      <div className={`evidence-tab ${riskColorClass}`} />

      <div className="evidence-content">
        {/* Header row */}
        <div className="evidence-header">
          <div className="evidence-meta">
            <span className="mono-id">{review.contract_id}</span>
            <span className="category-label">{review.clause_type}</span>
          </div>
          <RiskBadge riskLevel={review.risk_level} />
        </div>

        {/* Evidence blocks */}
        <div className="evidence-blocks">
          {/* Contract clause */}
          <div className="evidence-block">
            <span className="evidence-label">Contract Clause</span>
            <blockquote className="evidence-quote">
              <span className="quote-mark">&ldquo;</span>
              {review.contract_evidence}
              <span className="quote-mark">&rdquo;</span>
            </blockquote>
          </div>

          {/* Company standard */}
          <div className="evidence-block">
            <span className="evidence-label">
              Company Standard — <span className="mono-id">{review.standard_id}</span>
            </span>
            <blockquote className="evidence-quote standard-quote">
              <span className="quote-mark">&ldquo;</span>
              {review.standard_text}
              <span className="quote-mark">&rdquo;</span>
            </blockquote>
          </div>
        </div>

        {/* Reason */}
        <div className="evidence-reason">
          <span className="evidence-label">Why</span>
          <p>{review.reason}</p>
        </div>

        {/* Metadata */}
        <div className="evidence-metadata">
          {review.grounding_passed !== null && (
            <span className={`metadata-tag ${review.grounding_passed ? "grounded" : "ungrounded"}`}>
              {review.grounding_passed ? "✓ Evidence Verified" : "⚠ Unverified"}
            </span>
          )}
          {review.cached && <span className="metadata-tag cached">Cached</span>}
          <span className="metadata-tag latency">{review.latency_ms}ms</span>
        </div>

        {/* Actions footer */}
        <div className="evidence-footer">
          <ReviewActions reviewId={review.id} />
        </div>
      </div>
    </div>
  );
}
