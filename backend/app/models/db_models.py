"""
SQLAlchemy ORM models: ReviewResult, ReviewDecision, QueryLog.
See Plan.md §12 for the full schema specification.

Uses Base.metadata.create_all() on startup — no migration tool needed
for a 4-hour prototype. Alembic would be introduced for production
schema evolution.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReviewResult(Base):
    """Persisted result of a contract clause review."""
    __tablename__ = "review_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_generate_uuid)
    contract_id: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    contract_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_id: Mapped[str] = mapped_column(String, nullable=False)
    standard_text: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    llm_called: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ReviewDecision(Base):
    """Human-in-the-loop action on a review result."""
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_generate_uuid)
    review_result_id: Mapped[str] = mapped_column(
        String, ForeignKey("review_results.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String, nullable=False)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class QueryLog(Base):
    """Per-request diagnostic log for the observability view."""
    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String, nullable=False)
    contract_id: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    input_mode: Mapped[str] = mapped_column(String, nullable=False)
    intent_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False)
    stage_timings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    grounding_method: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_retries: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
