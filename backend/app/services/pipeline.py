"""
Pipeline orchestrator — chains all service steps for a single review request.
See Plan.md §3 (services/pipeline.py):
  segmenter -> classifier -> standards -> gap_check -> cache -> llm_judge -> grounding -> persist

Each step logs its own timing for the diagnostics/observability view.
"""

import json
import logging
import time
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.loader import LoadedData
from app.models.db_models import ReviewResult, QueryLog
from app.models.schemas import RiskLevel, InputMode, GroundingMethod
from app.services.segmenter import segment_contract
from app.services.classifier import classify_clauses
from app.services.intent import classify_intent, IntentResult
from app.services.standards import lookup_standard
from app.services.gap_check import check_gap
from app.services.cache import get_cached_result, store_result
from app.services.llm_judge import call_llm_judge
from app.services.grounding import validate_grounding

logger = logging.getLogger(__name__)


async def run_review_pipeline(
    contract_id: str,
    category: Optional[str],
    question: Optional[str],
    data: LoadedData,
    db: AsyncSession,
) -> tuple[ReviewResult, Optional[IntentResult]]:
    """
    Run the full review pipeline for a contract + category (or question).

    Returns (ReviewResult, IntentResult_or_None).
    Raises ValueError for invalid input (unknown contract, ambiguous intent, etc.).
    """
    request_id = str(uuid.uuid4())
    pipeline_start = time.time()
    stage_timings: dict[str, float] = {}
    intent_result: Optional[IntentResult] = None
    input_mode = InputMode.DIRECT_CATEGORY

    log_extra = {"request_id": request_id, "contract_id": contract_id}

    # --- Validate contract ---
    if contract_id not in data.contracts:
        raise ValueError(f"Unknown contract_id: '{contract_id}'")

    contract = data.contracts[contract_id]

    # --- Intent classification (if question provided) ---
    if question:
        input_mode = InputMode.FREE_TEXT_QUESTION
        t0 = time.time()
        intent_result = classify_intent(question)
        stage_timings["intent_ms"] = round((time.time() - t0) * 1000)

        if intent_result.ambiguous:
            # Log the ambiguous intent query
            query_log = QueryLog(
                request_id=request_id,
                contract_id=contract_id,
                category="ambiguous",
                input_mode=input_mode.value,
                intent_ambiguous=True,
                stage_timings_json=json.dumps(stage_timings),
                cache_hit=False,
            )
            db.add(query_log)
            await db.commit()
            raise ValueError("ambiguous_intent")

        category = intent_result.category

    if not category:
        raise ValueError("No category resolved — this should not happen")

    log_extra["category"] = category

    # --- Cache check ---
    t0 = time.time()
    cached = await get_cached_result(contract_id, category, db)
    stage_timings["cache_ms"] = round((time.time() - t0) * 1000)

    if cached is not None:
        # Log the cache hit
        total_ms = round((time.time() - pipeline_start) * 1000)
        query_log = QueryLog(
            request_id=request_id,
            contract_id=contract_id,
            category=category,
            input_mode=input_mode.value,
            intent_ambiguous=False,
            stage_timings_json=json.dumps(stage_timings),
            cache_hit=True,
        )
        db.add(query_log)
        await db.commit()

        logger.info(
            f"Pipeline complete (cached): {contract_id}/{category} in {total_ms}ms",
            extra={**log_extra, "stage": "pipeline", "duration_ms": total_ms},
        )
        return cached, intent_result

    # --- Segment contract ---
    t0 = time.time()
    clauses = segment_contract(contract.raw_text)
    stage_timings["segment_ms"] = round((time.time() - t0) * 1000)

    # --- Classify clauses ---
    t0 = time.time()
    classified = classify_clauses(clauses)
    stage_timings["classify_ms"] = round((time.time() - t0) * 1000)

    # --- Standard lookup ---
    standard = lookup_standard(category, data)
    if standard is None:
        raise ValueError(f"No company standard found for category: '{category}'")

    # --- Gap check ---
    t0 = time.time()
    gap_result = check_gap(category, classified)
    stage_timings["gap_check_ms"] = round((time.time() - t0) * 1000)

    if not gap_result.clause_present:
        # Short-circuit: no LLM call needed
        result = ReviewResult(
            contract_id=contract_id,
            category=category,
            risk_level=RiskLevel.NOT_ENOUGH_INFO.value,
            reason=f"The provided excerpt for this contract does not include a {category} clause.",
            contract_evidence=None,
            standard_id=standard.id,
            standard_text=standard.standard,
            grounding_passed=False,
            latency_ms=round((time.time() - pipeline_start) * 1000),
            llm_called=False,
        )
        await store_result(result, db)

        # Log
        query_log = QueryLog(
            request_id=request_id,
            contract_id=contract_id,
            category=category,
            input_mode=input_mode.value,
            intent_ambiguous=False,
            stage_timings_json=json.dumps(stage_timings),
            cache_hit=False,
            grounding_method=None,
            llm_retries=0,
        )
        db.add(query_log)
        await db.commit()

        logger.info(
            f"Pipeline complete (gap-checked, no LLM): {contract_id}/{category}",
            extra={**log_extra, "stage": "pipeline", "duration_ms": result.latency_ms},
        )
        return result, intent_result

    # --- LLM judgment ---
    clause = gap_result.classified_clause
    assert clause is not None  # guaranteed by gap_check

    t0 = time.time()
    llm_result = await call_llm_judge(
        category=category,
        contract_clause_text=clause.text,
        standard_id=standard.id,
        standard_text=standard.standard,
    )
    stage_timings["llm_ms"] = round((time.time() - t0) * 1000)

    # If LLM itself errored, skip grounding
    if llm_result.error:
        result = ReviewResult(
            contract_id=contract_id,
            category=category,
            risk_level=llm_result.risk_level,
            reason=llm_result.reason,
            contract_evidence=None,
            standard_id=standard.id,
            standard_text=standard.standard,
            grounding_passed=False,
            latency_ms=round((time.time() - pipeline_start) * 1000),
            llm_called=True,
        )
        await store_result(result, db)

        query_log = QueryLog(
            request_id=request_id,
            contract_id=contract_id,
            category=category,
            input_mode=input_mode.value,
            intent_ambiguous=False,
            stage_timings_json=json.dumps(stage_timings),
            cache_hit=False,
            grounding_method=GroundingMethod.FAILED.value,
            llm_retries=llm_result.retries_used,
        )
        db.add(query_log)
        await db.commit()

        return result, intent_result

    # --- Grounding validation ---
    t0 = time.time()
    grounding = validate_grounding(
        contract_evidence_quote=llm_result.contract_evidence_quote,
        standard_evidence_quote=llm_result.standard_evidence_quote,
        contract_source_text=clause.text,
        standard_source_text=standard.standard,
    )
    stage_timings["grounding_ms"] = round((time.time() - t0) * 1000)

    grounding_passed = grounding.contract_grounded and grounding.standard_grounded

    # Determine the overall grounding method for logging
    if grounding_passed:
        if grounding.contract_method == "fuzzy" or grounding.standard_method == "fuzzy":
            grounding_method = GroundingMethod.FUZZY
        else:
            grounding_method = GroundingMethod.STRICT
    else:
        grounding_method = GroundingMethod.FAILED

    if grounding_passed:
        # Use original source text, NOT LLM's echoed copy (Plan.md §10 step 4)
        result = ReviewResult(
            contract_id=contract_id,
            category=category,
            risk_level=llm_result.risk_level,
            reason=llm_result.reason,
            contract_evidence=clause.text,  # original, from our data
            standard_id=standard.id,
            standard_text=standard.standard,  # original, from our data
            grounding_passed=True,
            latency_ms=round((time.time() - pipeline_start) * 1000),
            llm_called=True,
        )
    else:
        # Grounding failed — downgrade to NEI
        result = ReviewResult(
            contract_id=contract_id,
            category=category,
            risk_level=RiskLevel.NOT_ENOUGH_INFO.value,
            reason="The system could not verify its evidence against the source text, so no reliable assessment is shown. Please review this clause manually.",
            contract_evidence=None,
            standard_id=standard.id,
            standard_text=standard.standard,
            grounding_passed=False,
            latency_ms=round((time.time() - pipeline_start) * 1000),
            llm_called=True,
        )

    await store_result(result, db)

    # Log
    query_log = QueryLog(
        request_id=request_id,
        contract_id=contract_id,
        category=category,
        input_mode=input_mode.value,
        intent_ambiguous=False,
        stage_timings_json=json.dumps(stage_timings),
        cache_hit=False,
        grounding_method=grounding_method.value,
        llm_retries=llm_result.retries_used,
    )
    db.add(query_log)
    await db.commit()

    total_ms = round((time.time() - pipeline_start) * 1000)
    logger.info(
        f"Pipeline complete: {contract_id}/{category} -> {result.risk_level} in {total_ms}ms",
        extra={**log_extra, "stage": "pipeline", "duration_ms": total_ms},
    )

    return result, intent_result
