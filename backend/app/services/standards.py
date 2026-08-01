"""
Standard lookup — trivial dictionary lookup by category.
See Plan.md §7.

No fuzzy matching needed — categories are a fixed closed set of 7 exact strings
shared by both the contract classifier output and company_standards.json.
"""

import logging

from app.data.loader import LoadedData, StandardData

logger = logging.getLogger(__name__)


def lookup_standard(category: str, data: LoadedData) -> StandardData | None:
    """
    Look up the company-approved standard for a given category.
    Returns None if the category is not found (should not happen with
    the fixed 7-category set, but defensive coding).
    """
    standard = data.standards.get(category)
    if standard is None:
        logger.warning(
            f"No standard found for category: '{category}'",
            extra={"stage": "standards", "category": category},
        )
    return standard
