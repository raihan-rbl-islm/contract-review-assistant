"""
LLM judgment step — Gemini API call with structured JSON output.
Only called when gap_check confirms the clause exists.
See Plan.md §9.

Uses structured output (response_mime_type: application/json) so the model
is schema-constrained. 'Not Enough Information' is deliberately excluded from
the LLM's allowed enum — that state is only produced by gap_check.py.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.config import settings

logger = logging.getLogger(__name__)


# Structured output schema for the Gemini response.
# Note: 'Not Enough Information' is NOT in the enum — see Plan.md §9.1.
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "risk_level": {"type": "string", "enum": ["Low Risk", "Medium Risk", "High Risk"]},
        "reason": {"type": "string"},
        "contract_evidence_quote": {"type": "string"},
        "standard_evidence_quote": {"type": "string"},
    },
    "required": ["risk_level", "reason", "contract_evidence_quote", "standard_evidence_quote"],
}

# Prompt template — verbatim from Plan.md §9.2
_PROMPT_TEMPLATE = """You are assisting a human contract reviewer. You are not a lawyer and must not give
legal advice. You will be given a contract clause and a company-approved standard for
the same category. Compare them factually and return your answer in the required JSON
format only.

Rules:
- Base your answer only on the two texts provided below. Do not use outside knowledge
  of contract law or assume anything not stated in the text.
- contract_evidence_quote and standard_evidence_quote must be copied exactly,
  word-for-word, from the text provided below. Do not paraphrase, summarize, or
  combine sentences in these two fields.
- risk_level meanings:
  Low Risk = the contract clause matches or gives equal/better protection than the
    standard.
  Medium Risk = the clause differs from the standard in a limited or negotiable way.
  High Risk = the clause clearly conflicts with the standard or creates a major risk.
- reason must be one or two plain-language sentences a non-lawyer can understand,
  explaining the specific difference (e.g. numbers, time periods, or obligations that
  differ).

Clause category: {category}

Contract clause text:
\"\"\"
{contract_clause_text}
\"\"\"

Company standard ({standard_id}):
\"\"\"
{standard_text}
\"\"\"

Return only the JSON object, no other text."""


@dataclass
class LLMJudgmentResult:
    """Result from the LLM judgment call."""
    risk_level: str
    reason: str
    contract_evidence_quote: str
    standard_evidence_quote: str
    retries_used: int = 0
    error: bool = False
    error_message: str | None = None


def _configure_client() -> None:
    """Configure the Gemini client with the API key."""
    genai.configure(api_key=settings.gemini_api_key)


async def call_llm_judge(
    category: str,
    contract_clause_text: str,
    standard_id: str,
    standard_text: str,
) -> LLMJudgmentResult:
    """
    Call Gemini to compare a contract clause against a company standard.

    Retries up to 2 times on transient errors with exponential backoff
    (0.5s, 1.5s). On final failure, returns a soft-failure 'Not Enough
    Information' result rather than crashing. See Plan.md §9.2a.
    """
    _configure_client()

    prompt = _PROMPT_TEMPLATE.format(
        category=category,
        contract_clause_text=contract_clause_text,
        standard_id=standard_id,
        standard_text=standard_text,
    )

    model = genai.GenerativeModel("gemini-2.0-flash")

    max_retries = 2
    backoff_delays = [0.5, 1.5]
    retries_used = 0

    for attempt in range(max_retries + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": _RESPONSE_SCHEMA,
                },
            )

            # Parse the JSON response
            response_text = response.text
            parsed = json.loads(response_text)

            # Validate the response shape (Pydantic-level validation happens upstream)
            risk_level = parsed.get("risk_level", "")
            if risk_level not in ("Low Risk", "Medium Risk", "High Risk"):
                raise ValueError(f"Invalid risk_level from LLM: '{risk_level}'")

            reason = parsed.get("reason", "")
            contract_quote = parsed.get("contract_evidence_quote", "")
            standard_quote = parsed.get("standard_evidence_quote", "")

            if not contract_quote or not standard_quote:
                raise ValueError("LLM returned empty evidence quotes")

            logger.info(
                f"LLM judgment complete: {risk_level}",
                extra={
                    "stage": "llm_judge",
                    "category": category,
                    "risk_level": risk_level,
                },
            )

            return LLMJudgmentResult(
                risk_level=risk_level,
                reason=reason,
                contract_evidence_quote=contract_quote,
                standard_evidence_quote=standard_quote,
                retries_used=retries_used,
            )

        except (
            google_exceptions.ServiceUnavailable,
            google_exceptions.ResourceExhausted,
            google_exceptions.DeadlineExceeded,
        ) as e:
            retries_used += 1
            if attempt < max_retries:
                delay = backoff_delays[attempt]
                logger.warning(
                    f"LLM transient error (attempt {attempt + 1}/{max_retries + 1}), "
                    f"retrying in {delay}s: {e}",
                    extra={"stage": "llm_judge", "category": category},
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"LLM failed after {max_retries + 1} attempts: {e}",
                    extra={"stage": "llm_judge", "category": category},
                )
                return LLMJudgmentResult(
                    risk_level="Not Enough Information",
                    reason="The review service is temporarily unavailable. Please try again or review this clause manually.",
                    contract_evidence_quote="",
                    standard_evidence_quote="",
                    retries_used=retries_used,
                    error=True,
                    error_message=str(e),
                )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(
                f"LLM response parsing error: {e}",
                extra={"stage": "llm_judge", "category": category},
            )
            return LLMJudgmentResult(
                risk_level="Not Enough Information",
                reason="The system could not process the review response. Please try again or review this clause manually.",
                contract_evidence_quote="",
                standard_evidence_quote="",
                retries_used=retries_used,
                error=True,
                error_message=str(e),
            )

        except Exception as e:
            logger.error(
                f"Unexpected LLM error: {e}",
                extra={"stage": "llm_judge", "category": category},
            )
            return LLMJudgmentResult(
                risk_level="Not Enough Information",
                reason="The review service is temporarily unavailable. Please try again or review this clause manually.",
                contract_evidence_quote="",
                standard_evidence_quote="",
                retries_used=retries_used,
                error=True,
                error_message=str(e),
            )

    # Should not reach here, but defensive
    return LLMJudgmentResult(
        risk_level="Not Enough Information",
        reason="The review service is temporarily unavailable.",
        contract_evidence_quote="",
        standard_evidence_quote="",
        retries_used=retries_used,
        error=True,
    )
