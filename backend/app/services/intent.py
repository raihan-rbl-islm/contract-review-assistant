"""
Intent classification — resolves a free-text question to one of the 7
canonical categories WITHOUT an LLM call.
See Plan.md §6a (REQUIRED, not optional).

Algorithm:
1. Reuse CATEGORY_KEYWORDS plus question-phrasing synonyms.
2. Score each category by counting keyword hits (case-insensitive) in the
   question text. Return the highest-scoring category.
3. If the top two scores are tied or the top score is 0, return 'ambiguous'
   so the frontend can show the manual category picker.
"""

import logging
import re
from dataclasses import dataclass

class AmbiguousIntentError(Exception):
    def __init__(self, candidate_categories: list[str]):
        self.candidate_categories = candidate_categories
        super().__init__(f"Ambiguous intent. Candidates: {candidate_categories}")

logger = logging.getLogger(__name__)


# Extended keyword map: CATEGORY_KEYWORDS from classifier.py plus
# question-phrasing synonyms per Plan.md §6a.
INTENT_KEYWORDS: dict[str, list[str]] = {
    "Payment": [
        "payment", "invoice", "fee", "pay", "paid", "billing",
        "undisputed invoice", "late fee",
    ],
    "Termination": [
        "termination", "terminate", "end the agreement",
        "terminate for convenience", "termination for breach",
        "termination-for-breach", "terminate for breach",
    ],
    "Data Protection": [
        "data protection", "security", "breach notice", "subprocessor", "subprocessors",
        "use of data", "data return", "data deletion",
        "data breach", "encryption", "encrypt", "stored data",
        "personal data", "breach notification",
    ],
    "Confidentiality": [
        "confidentiality", "confidential", "confidentiality period",
        "confidential information",
    ],
    "Automatic Renewal": [
        "automatic renewal", "renewal", "renews",
        "renew automatically", "renewal notice",
        "stop renewal", "stop automatic renewal",
        "renewal clause",
    ],
    "Intellectual Property": [
        "intellectual property", "ownership", "ip",
        "custom work", "owns", "own", "campaign materials",
        "ownership of",
    ],
    "Limitation of Liability": [
        "limitation of liability", "liability",
        "liability cap", "total liability",
        "liability limit",
    ],
}


@dataclass
class IntentResult:
    """Result of intent classification."""
    category: str | None       # resolved category, or None if ambiguous
    ambiguous: bool            # True if classification could not confidently resolve
    candidate_categories: list[str]  # top candidates when ambiguous
    scores: dict[str, int]     # full score breakdown for debugging/explainability


def classify_intent(question: str) -> IntentResult:
    """
    Classify a free-text question into one of the 7 canonical categories.

    Returns an IntentResult. If ambiguous is True, the caller should prompt
    the user to pick a category manually.
    """
    question_lower = question.lower()

    # Score each category by counting keyword hits
    scores: dict[str, int] = {}
    for category, keywords in INTENT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", question_lower):
                score += 1
        scores[category] = score

    # Sort by score descending
    sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_score = sorted_categories[0][1]

    # If top score is 0, we matched nothing — ambiguous
    if top_score == 0:
        logger.info(
            "Intent classification: no keyword matches, returning ambiguous",
            extra={"stage": "intent"},
        )
        return IntentResult(
            category=None,
            ambiguous=True,
            candidate_categories=[cat for cat, _ in sorted_categories[:3]],
            scores=scores,
        )

    # Check for tie between top two
    if len(sorted_categories) >= 2 and sorted_categories[1][1] == top_score:
        tied = [cat for cat, s in sorted_categories if s == top_score]
        logger.info(
            f"Intent classification: tie between {tied}, returning ambiguous",
            extra={"stage": "intent"},
        )
        return IntentResult(
            category=None,
            ambiguous=True,
            candidate_categories=tied,
            scores=scores,
        )

    # Clear winner
    winner = sorted_categories[0][0]
    logger.info(
        f"Intent classification: resolved to '{winner}' (score={top_score})",
        extra={"stage": "intent"},
    )
    return IntentResult(
        category=winner,
        ambiguous=False,
        candidate_categories=[winner],
        scores=scores,
    )
