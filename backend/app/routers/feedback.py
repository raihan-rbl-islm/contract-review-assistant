"""
Feedback router — human-in-the-loop decision endpoint.
See Plan.md §13: POST /api/review/{id}/decision
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import ReviewResult, ReviewDecision
from app.models.schemas import DecisionRequest, DecisionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/review/{review_id}/decision", response_model=DecisionResponse)
async def submit_decision(
    review_id: str,
    body: DecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a human decision on a review result.
    This is the human-in-the-loop action endpoint — nothing here calls the LLM.
    """
    # Verify the review result exists
    stmt = select(ReviewResult).where(ReviewResult.id == review_id)
    result = await db.execute(stmt)
    review = result.scalar_one_or_none()

    if review is None:
        raise HTTPException(status_code=404, detail=f"Review result not found: {review_id}")

    # Create the decision record
    decision = ReviewDecision(
        review_result_id=review_id,
        decision=body.decision.value,
        feedback_text=body.feedback_text,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)

    logger.info(
        f"Decision recorded: {body.decision.value} for review {review_id}",
        extra={
            "stage": "feedback",
            "contract_id": review.contract_id,
            "category": review.category,
        },
    )

    return DecisionResponse(
        id=decision.id,
        review_result_id=decision.review_result_id,
        decision=body.decision,
        feedback_text=decision.feedback_text,
        created_at=decision.created_at,
    )
