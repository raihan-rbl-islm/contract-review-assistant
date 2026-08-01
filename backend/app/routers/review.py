"""
Review router — handles contract listing, category listing, test questions,
and the main review endpoint.
See Plan.md §13.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.data.loader import LoadedData
from app.models.schemas import (
    ReviewRequest,
    ReviewResponse,
    ContractSummary,
    TestQuestionResponse,
    AmbiguousIntentResponse,
    RiskLevel,
)
from app.services.pipeline import run_review_pipeline
from app.services.classifier import CANONICAL_CATEGORIES
from app.services.intent import AmbiguousIntentError

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_data(request: Request) -> LoadedData:
    """Dependency to get loaded data from app.state."""
    return request.app.state.data


@router.get("/contracts", response_model=list[ContractSummary])
async def list_contracts(data: LoadedData = Depends(_get_data)):
    """List all available contracts with their IDs and titles."""
    return [
        ContractSummary(id=c.id, title=c.title)
        for c in sorted(data.contracts.values(), key=lambda x: x.id)
    ]


@router.get("/categories", response_model=list[str])
async def list_categories():
    """List the 7 canonical clause categories."""
    return CANONICAL_CATEGORIES


@router.get("/test-questions", response_model=list[TestQuestionResponse])
async def list_test_questions(data: LoadedData = Depends(_get_data)):
    """List public test questions + missing-info cases for the sample dropdown."""
    items: list[TestQuestionResponse] = []

    for pq in data.public_test_questions:
        items.append(TestQuestionResponse(
            id=pq.id,
            contract_id=pq.contract_id,
            question=pq.question,
            group="public_test",
        ))

    for mi in data.missing_info_cases:
        items.append(TestQuestionResponse(
            id=mi.id,
            contract_id=mi.contract_id,
            question=mi.question,
            group="missing_info",
            expected_behaviour=mi.expected_behaviour,
        ))

    return items


@router.post("/review", response_model=ReviewResponse)
async def create_review(
    body: ReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    data: LoadedData = Depends(_get_data),
):
    """
    Run a contract clause review.

    Accepts EITHER {contract_id, category} OR {contract_id, question}.
    When question is given, runs intent classification first.
    If intent is ambiguous, returns 422 with candidate categories.
    """
    try:
        result, intent_result, was_cached = await run_review_pipeline(
            contract_id=body.contract_id,
            category=body.category,
            question=body.question,
            data=data,
            db=db,
        )
    except AmbiguousIntentError as e:
        raise HTTPException(
            status_code=422,
            detail=AmbiguousIntentResponse(
                candidate_categories=e.candidate_categories
            ).model_dump(),
        )
    except ValueError as e:
        error_msg = str(e)
        if "Unknown contract_id" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)

        raise HTTPException(status_code=400, detail=error_msg)

    return ReviewResponse(
        id=result.id,
        contract_id=result.contract_id,
        clause_type=result.category,
        risk_level=RiskLevel(result.risk_level),
        contract_evidence=result.contract_evidence,
        standard_id=result.standard_id,
        standard_text=result.standard_text,
        reason=result.reason,
        human_review_required=True,
        cached=was_cached,
        grounding_passed=result.grounding_passed,
        latency_ms=result.latency_ms,
    )
