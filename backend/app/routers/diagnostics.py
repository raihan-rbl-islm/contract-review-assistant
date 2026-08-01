"""
Diagnostics router — observability endpoints for latency stats and query logs.
See Plan.md §13: GET /api/diagnostics/latency, GET /api/diagnostics/logs
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import QueryLog, ReviewResult
from app.models.schemas import LatencyStats, QueryLogEntry, InputMode, GroundingMethod

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/diagnostics/latency", response_model=LatencyStats)
async def get_latency_stats(db: AsyncSession = Depends(get_db)):
    """
    Aggregated stage timings, cache hit rate, total LLM calls.
    Powers the Observability rubric demo.
    """
    # Total reviews
    total_stmt = select(func.count(ReviewResult.id))
    total_result = await db.execute(total_stmt)
    total_reviews = total_result.scalar() or 0

    if total_reviews == 0:
        return LatencyStats()

    # Latency stats from review_results
    stats_stmt = select(
        func.avg(ReviewResult.latency_ms),
        func.min(ReviewResult.latency_ms),
        func.max(ReviewResult.latency_ms),
        func.sum(func.cast(ReviewResult.llm_called, type_=lambda: None)),  # noqa
    )
    # Simpler approach: get all results and compute in Python
    all_results_stmt = select(ReviewResult)
    all_results = await db.execute(all_results_stmt)
    results = all_results.scalars().all()

    latencies = [r.latency_ms for r in results]
    llm_calls = sum(1 for r in results if r.llm_called)

    # Cache hit rate from query_logs
    cache_stmt = select(QueryLog)
    cache_result = await db.execute(cache_stmt)
    logs = cache_result.scalars().all()

    total_queries = len(logs)
    cache_hits = sum(1 for log in logs if log.cache_hit)
    cache_hit_rate = cache_hits / total_queries if total_queries > 0 else 0.0

    # Stage averages from query_logs
    stage_totals: dict[str, list[float]] = {}
    for log in logs:
        if log.stage_timings_json:
            try:
                timings = json.loads(log.stage_timings_json)
                for stage, ms in timings.items():
                    if stage not in stage_totals:
                        stage_totals[stage] = []
                    stage_totals[stage].append(ms)
            except json.JSONDecodeError:
                pass

    stage_averages = {
        stage: round(sum(vals) / len(vals), 1)
        for stage, vals in stage_totals.items()
    }

    return LatencyStats(
        total_reviews=total_reviews,
        cache_hit_rate=round(cache_hit_rate, 3),
        total_llm_calls=llm_calls,
        avg_latency_ms=round(sum(latencies) / len(latencies), 1) if latencies else 0,
        min_latency_ms=min(latencies) if latencies else 0,
        max_latency_ms=max(latencies) if latencies else 0,
        stage_averages=stage_averages,
    )


@router.get("/diagnostics/logs", response_model=list[QueryLogEntry])
async def get_query_logs(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Last N query_logs rows, most recent first."""
    stmt = (
        select(QueryLog)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        QueryLogEntry(
            id=row.id,
            request_id=row.request_id,
            contract_id=row.contract_id,
            category=row.category,
            input_mode=InputMode(row.input_mode),
            intent_ambiguous=row.intent_ambiguous,
            stage_timings_json=row.stage_timings_json,
            cache_hit=row.cache_hit,
            grounding_method=GroundingMethod(row.grounding_method) if row.grounding_method else None,
            llm_retries=row.llm_retries,
            created_at=row.created_at,
        )
        for row in rows
    ]
