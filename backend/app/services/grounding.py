"""
Grounding validation — verifies that LLM-returned evidence is a real substring
of the source text. See Plan.md §10.

1. Normalize whitespace and quote characters on both sides.
2. Strict substring check first.
3. Fuzzy fallback (difflib SequenceMatcher, ratio ≥ 0.9) if strict fails.
4. If both fail, downgrade to 'Not Enough Information' and log distinctly.
"""

import difflib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GroundingResult:
    """Result of grounding validation."""
    contract_grounded: bool
    standard_grounded: bool
    contract_method: str | None = None   # "strict", "fuzzy", or "failed"
    standard_method: str | None = None
    contract_fuzzy_ratio: float | None = None
    standard_fuzzy_ratio: float | None = None


def _normalize(text: str) -> str:
    """
    Normalize whitespace and quote characters for comparison.
    Collapse multiple spaces/newlines to single spaces, strip,
    and normalize curly quotes/apostrophes to straight ones.
    """
    # Normalize curly quotes to straight
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _check_grounding(quote: str, source_text: str) -> tuple[bool, str, float | None]:
    """
    Check if a quote is grounded in the source text.
    Returns (is_grounded, method, fuzzy_ratio_if_applicable).
    """
    normalized_quote = _normalize(quote)
    normalized_source = _normalize(source_text)

    if not normalized_quote:
        return False, "failed", None

    # 1. Strict substring check
    if normalized_quote in normalized_source:
        return True, "strict", None

    # 2. Fuzzy fallback — SequenceMatcher ratio against the full source
    ratio = difflib.SequenceMatcher(None, normalized_quote, normalized_source).ratio()

    if ratio >= 0.9:
        logger.info(
            f"grounding_fuzzy_accept",
            extra={"stage": "grounding", "ratio": ratio},
        )
        return True, "fuzzy", ratio

    # 3. Try sliding window for better fuzzy match on long sources
    # Use a window roughly the size of the quote
    quote_len = len(normalized_quote)
    best_ratio = ratio
    for i in range(0, max(1, len(normalized_source) - quote_len + 1), quote_len // 4 or 1):
        window = normalized_source[i : i + quote_len + 20]  # slight overshoot
        window_ratio = difflib.SequenceMatcher(None, normalized_quote, window).ratio()
        if window_ratio > best_ratio:
            best_ratio = window_ratio

    if best_ratio >= 0.9:
        logger.info(
            f"grounding_fuzzy_accept (windowed)",
            extra={"stage": "grounding", "ratio": best_ratio},
        )
        return True, "fuzzy", best_ratio

    # Failed
    logger.warning(
        f"grounding_failed",
        extra={"stage": "grounding", "best_ratio": best_ratio},
    )
    return False, "failed", best_ratio


def validate_grounding(
    contract_evidence_quote: str,
    standard_evidence_quote: str,
    contract_source_text: str,
    standard_source_text: str,
) -> GroundingResult:
    """
    Validate that the LLM's evidence quotes are real substrings of their
    respective source texts.
    """
    c_grounded, c_method, c_ratio = _check_grounding(
        contract_evidence_quote, contract_source_text
    )
    s_grounded, s_method, s_ratio = _check_grounding(
        standard_evidence_quote, standard_source_text
    )

    return GroundingResult(
        contract_grounded=c_grounded,
        standard_grounded=s_grounded,
        contract_method=c_method,
        standard_method=s_method,
        contract_fuzzy_ratio=c_ratio,
        standard_fuzzy_ratio=s_ratio,
    )
