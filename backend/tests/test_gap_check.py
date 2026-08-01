"""
Tests for gap_check — verifies that the 3 missing_information_cases correctly
detect absent clauses and short-circuit before any LLM call.
See Plan.md §8.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.segmenter import segment_contract
from app.services.classifier import classify_clauses
from app.services.gap_check import check_gap


_CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "problem Datasets" / "contracts"


def _load_contract(contract_id: str) -> str:
    path = _CONTRACTS_DIR / f"{contract_id}.txt"
    return path.read_text(encoding="utf-8")


def _get_classified(contract_id: str) -> dict:
    raw = _load_contract(contract_id)
    clauses = segment_contract(raw)
    return classify_clauses(clauses)


class TestGapCheckMissingInfo:
    """MI-01, MI-02, MI-03: must detect missing clauses and return clause_present=False."""

    def test_mi01_c004_no_automatic_renewal(self):
        """C-004 has no automatic renewal clause."""
        classified = _get_classified("C-004")
        result = check_gap("Automatic Renewal", classified)
        assert result.clause_present is False
        assert result.classified_clause is None

    def test_mi02_c007_no_termination(self):
        """C-007 has no termination clause."""
        classified = _get_classified("C-007")
        result = check_gap("Termination", classified)
        assert result.clause_present is False
        assert result.classified_clause is None

    def test_mi03_c008_no_limitation_of_liability(self):
        """C-008 has no limitation of liability clause."""
        classified = _get_classified("C-008")
        result = check_gap("Limitation of Liability", classified)
        assert result.clause_present is False
        assert result.classified_clause is None


class TestGapCheckPresent:
    """Sanity: categories that DO exist should return clause_present=True."""

    def test_c001_payment_present(self):
        classified = _get_classified("C-001")
        result = check_gap("Payment", classified)
        assert result.clause_present is True
        assert result.classified_clause is not None

    def test_c001_automatic_renewal_present(self):
        classified = _get_classified("C-001")
        result = check_gap("Automatic Renewal", classified)
        assert result.clause_present is True

    def test_c003_data_protection_present(self):
        classified = _get_classified("C-003")
        result = check_gap("Data Protection", classified)
        assert result.clause_present is True
