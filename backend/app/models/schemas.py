"""
Pydantic request/response models.
See Plan.md §13 for the API contract shapes.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, model_validator


# --- Enums ---

class RiskLevel(str, Enum):
    LOW = "Low Risk"
    MEDIUM = "Medium Risk"
    HIGH = "High Risk"
    NOT_ENOUGH_INFO = "Not Enough Information"


class DecisionType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    MARK_FOR_REVIEW = "mark_for_review"


class InputMode(str, Enum):
    DIRECT_CATEGORY = "direct_category"
    FREE_TEXT_QUESTION = "free_text_question"


class GroundingMethod(str, Enum):
    STRICT = "strict"
    FUZZY = "fuzzy"
    FAILED = "failed"


# --- Request models ---

class ReviewRequest(BaseModel):
    """
    POST /api/review body.
    Exactly one of category or question must be provided.
    """
    contract_id: str
    category: Optional[str] = None
    question: Optional[str] = None

    @model_validator(mode="after")
    def exactly_one_of_category_or_question(self) -> "ReviewRequest":
        if self.category and self.question:
            raise ValueError("Provide exactly one of 'category' or 'question', not both.")
        if not self.category and not self.question:
            raise ValueError("Provide exactly one of 'category' or 'question'.")
        return self


class DecisionRequest(BaseModel):
    """POST /api/review/{id}/decision body."""
    decision: DecisionType
    feedback_text: Optional[str] = None


# --- Response models ---

class ContractSummary(BaseModel):
    """Returned by GET /api/contracts."""
    id: str
    title: str


class ReviewResponse(BaseModel):
    """Returned by POST /api/review."""
    id: str
    contract_id: str
    clause_type: str
    risk_level: RiskLevel
    contract_evidence: Optional[str] = None
    standard_id: str
    standard_text: str
    reason: str
    human_review_required: bool = True
    cached: bool = False
    grounding_passed: Optional[bool] = None
    latency_ms: int = 0


class AmbiguousIntentResponse(BaseModel):
    """Returned with 422 when intent classification is ambiguous."""
    error: str = "ambiguous_intent"
    candidate_categories: list[str]


class DecisionResponse(BaseModel):
    """Returned by POST /api/review/{id}/decision."""
    id: str
    review_result_id: str
    decision: DecisionType
    feedback_text: Optional[str] = None
    created_at: datetime


class TestQuestionResponse(BaseModel):
    """A single test question for the sample dropdown."""
    id: str
    contract_id: str
    question: str
    group: str  # "public_test" or "missing_info"
    expected_behaviour: Optional[str] = None


class LatencyStats(BaseModel):
    """Aggregated latency statistics for the diagnostics page."""
    total_reviews: int = 0
    cache_hit_rate: float = 0.0
    total_llm_calls: int = 0
    avg_latency_ms: float = 0.0
    min_latency_ms: int = 0
    max_latency_ms: int = 0
    stage_averages: dict[str, float] = {}


class QueryLogEntry(BaseModel):
    """A single query log row for the diagnostics page."""
    id: int
    request_id: str
    contract_id: str
    category: str
    input_mode: InputMode
    intent_ambiguous: bool = False
    stage_timings_json: Optional[str] = None
    cache_hit: bool = False
    grounding_method: Optional[GroundingMethod] = None
    llm_retries: int = 0
    created_at: datetime
