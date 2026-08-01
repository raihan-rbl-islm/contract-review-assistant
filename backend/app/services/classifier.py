"""
Category classification — maps extracted clause headings to one of 7 canonical
categories using a keyword dictionary (case-insensitive substring match).
See Plan.md §6.

When multiple clause instances map to the same category within one contract,
they are concatenated into a single combined clause block with sub-clauses
preserved for evidence display.
"""

import logging
import re
from dataclasses import dataclass, field

from app.services.segmenter import ClauseInstance

logger = logging.getLogger(__name__)


# Keyword dictionary for category classification.
# Order matters for priority: longer/more-specific keywords listed first within
# each category so they match before shorter ones.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Payment": ["payment", "invoice", "fee"],
    "Termination": ["termination", "terminate"],
    "Data Protection": [
        "data protection", "security", "breach notice", "subprocessor", "subprocessors",
        "use of data", "data return", "data deletion",
    ],
    "Confidentiality": ["confidentiality", "confidential"],
    "Automatic Renewal": ["automatic renewal", "renewal", "renews"],
    "Intellectual Property": ["intellectual property", "ownership", "ip"],
    "Limitation of Liability": ["limitation of liability", "liability"],
}

# The canonical set of 7 categories
CANONICAL_CATEGORIES: list[str] = list(CATEGORY_KEYWORDS.keys())


@dataclass
class ClassifiedClause:
    """A clause (or group of clauses) classified into a canonical category."""
    category: str
    section_number: str       # primary section number (first sub-clause)
    text: str                 # combined text for LLM analysis
    sub_clauses: list[ClauseInstance] = field(default_factory=list)


def _classify_heading(heading: str) -> str | None:
    """
    Classify a single clause heading into a canonical category.
    Uses case-insensitive substring matching on the heading text.
    Returns None if no category matches.
    """
    heading_lower = heading.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", heading_lower):
                return category
    return None


def _classify_by_body(body: str) -> str | None:
    """
    Fallback: classify by body-text keyword match if heading was ambiguous.
    """
    body_lower = body.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", body_lower):
                return category
    return None


def classify_clauses(clauses: list[ClauseInstance]) -> dict[str, ClassifiedClause]:
    """
    Map a list of extracted clauses to canonical categories.

    When multiple clauses map to the same category (e.g. C-003's five
    data-protection sub-clauses), they are merged into a single
    ClassifiedClause with concatenated text and preserved sub_clauses.

    Returns a dict keyed by category string.
    """
    result: dict[str, ClassifiedClause] = {}

    for clause in clauses:
        category = _classify_heading(clause.heading)
        if category is None:
            category = _classify_by_body(clause.text)
        if category is None:
            logger.warning(
                f"Could not classify clause heading: '{clause.heading}'",
                extra={"stage": "classifier"},
            )
            continue

        if category in result:
            # Merge into existing classified clause
            existing = result[category]
            existing.sub_clauses.append(clause)
            # Concatenate text with heading prefix for context
            existing.text += f"\n\n{clause.section_number} {clause.heading}\n{clause.text}"
        else:
            result[category] = ClassifiedClause(
                category=category,
                section_number=clause.section_number,
                text=f"{clause.section_number} {clause.heading}\n{clause.text}",
                sub_clauses=[clause],
            )

    logger.info(
        f"Classified into {len(result)} categories: {list(result.keys())}",
        extra={"stage": "classifier"},
    )
    return result
