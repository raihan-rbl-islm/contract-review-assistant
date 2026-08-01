"""
Regex-based clause segmentation.
Splits a contract's raw text into individual clauses by detecting numbered
section headings (e.g. '2.1 Payment', '7.1 Automatic Renewal').
See Plan.md §5.
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClauseInstance:
    """A single clause extracted from a contract."""
    heading: str
    section_number: str
    text: str


# Matches lines like "2.1 Payment", "10.1 Liability", etc.
_HEADING_PATTERN = re.compile(r"^(\d+\.\d+)\s+(.+)$", re.MULTILINE)

# The "Dataset Note:" block is meta-commentary from contest organizers,
# not contract content — always exclude it.
_DATASET_NOTE_PATTERN = re.compile(r"^Dataset Note:.*", re.MULTILINE | re.DOTALL)


def segment_contract(raw_text: str) -> list[ClauseInstance]:
    """
    Split contract text into a list of ClauseInstance objects.

    Algorithm:
    1. Find all heading lines matching the pattern ^\d+\.\d+\s+.+$
    2. For each heading, capture the text until the next heading (or end of
       file, or the 'Dataset Note:' line).
    3. Return the list of extracted clauses.
    """
    # Strip out the Dataset Note block before processing
    text_without_note = _DATASET_NOTE_PATTERN.sub("", raw_text).rstrip()

    headings = list(_HEADING_PATTERN.finditer(text_without_note))
    if not headings:
        logger.warning("No clause headings found in contract text")
        return []

    clauses: list[ClauseInstance] = []

    for i, match in enumerate(headings):
        section_number = match.group(1)
        heading = match.group(2).strip()

        # Clause body: from end of this heading line to start of next heading (or EOF)
        body_start = match.end()
        if i + 1 < len(headings):
            body_end = headings[i + 1].start()
        else:
            body_end = len(text_without_note)

        body = text_without_note[body_start:body_end].strip()

        clauses.append(ClauseInstance(
            heading=heading,
            section_number=section_number,
            text=body,
        ))

    logger.info(
        f"Segmented contract into {len(clauses)} clauses",
        extra={"stage": "segmenter"},
    )
    return clauses
