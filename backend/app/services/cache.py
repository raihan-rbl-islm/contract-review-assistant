"""
Caching layer — in-process + DB-backed result cache.
Key: (contract_id, category). See Plan.md §11.

On cache hit, skips the entire pipeline and returns the stored result
with cached=True and the original timestamp.
"""

import asyncio
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ReviewResult

logger = logging.getLogger(__name__)

# In-process cache: dict guarded by asyncio.Lock
_cache: dict[tuple[str, str], ReviewResult] = {}
_cache_lock = asyncio.Lock()


async def get_cached_result(
    contract_id: str,
    category: str,
    db: AsyncSession,
) -> Optional[ReviewResult]:
    """
    Check for a cached result. In-process first, then DB.
    Returns None on cache miss.
    """
    key = (contract_id, category)

    # 1. In-process cache check
    async with _cache_lock:
        if key in _cache:
            logger.info(
                f"Cache hit (in-process): {contract_id}/{category}",
                extra={"stage": "cache", "contract_id": contract_id, "category": category},
            )
            return _cache[key]

    # 2. DB-backed cache check
    stmt = select(ReviewResult).where(
        ReviewResult.contract_id == contract_id,
        ReviewResult.category == category,
    ).order_by(ReviewResult.created_at.desc()).limit(1)

    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row is not None:
        # Populate in-process cache for next time
        async with _cache_lock:
            _cache[key] = row
        logger.info(
            f"Cache hit (DB): {contract_id}/{category}",
            extra={"stage": "cache", "contract_id": contract_id, "category": category},
        )
        return row

    logger.info(
        f"Cache miss: {contract_id}/{category}",
        extra={"stage": "cache", "contract_id": contract_id, "category": category},
    )
    return None


async def store_result(
    result: ReviewResult,
    db: AsyncSession,
) -> None:
    """
    Store a review result in both the DB and in-process cache.
    """
    key = (result.contract_id, result.category)

    # DB persist
    db.add(result)
    await db.commit()
    await db.refresh(result)

    # In-process cache
    async with _cache_lock:
        _cache[key] = result

    logger.info(
        f"Result cached: {result.contract_id}/{result.category}",
        extra={"stage": "cache", "contract_id": result.contract_id, "category": result.category},
    )
