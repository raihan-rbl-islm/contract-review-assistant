"""
Gap detection — checks whether a requested category actually exists in a
contract's classified clauses BEFORE any LLM call.
See Plan.md §8.

If the clause is missing, returns immediately with 'Not Enough Information'
and zero Gemini calls. This guarantees the three missing_information_cases
(C-004 auto renewal, C-007 termination, C-008 limitation of liability)
can never hallucinate.
"""

import logging
from dataclasses import dataclass

from app.services.classifier import ClassifiedClause

logger = logging.getLogger(__name__)


@dataclass
class GapCheckResult:
    """Result of the gap check."""
    clause_present: bool
    classified_clause: ClassifiedClause | None = None


def check_gap(
    category: str,
    classified_clauses: dict[str, ClassifiedClause],
) -> GapCheckResult:
    """
    Check whether the requested category exists in the contract's clauses.

    Returns GapCheckResult with clause_present=False if the category is not
    found, allowing the pipeline to short-circuit before any LLM call.
    """
    clause = classified_clauses.get(category)

    if clause is None:
        logger.info(
            f"Gap detected: category '{category}' not present in contract",
            extra={"stage": "gap_check", "category": category},
        )
        return GapCheckResult(clause_present=False)

    logger.info(
        f"Clause found for category '{category}'",
        extra={"stage": "gap_check", "category": category},
    )
    return GapCheckResult(clause_present=True, classified_clause=clause)
