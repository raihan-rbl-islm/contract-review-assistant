"""
Tests for the category classifier.
Asserts that all 8 contracts' clauses are classified into the correct categories,
including C-003's 5 sub-clauses merging into a single 'Data Protection' entry.
See Plan.md §6.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.segmenter import segment_contract
from app.services.classifier import classify_clauses


_CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "problem Datasets" / "contracts"


def _load_contract(contract_id: str) -> str:
    path = _CONTRACTS_DIR / f"{contract_id}.txt"
    return path.read_text(encoding="utf-8")


class TestClassifierC001:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-001"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {
            "Payment", "Termination", "Automatic Renewal", "Limitation of Liability",
        }


class TestClassifierC002:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-002"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {
            "Payment", "Termination", "Confidentiality", "Intellectual Property",
        }


class TestClassifierC003:
    def test_all_map_to_data_protection(self):
        """All 5 sub-clauses in C-003 should merge into one 'Data Protection' entry."""
        clauses = segment_contract(_load_contract("C-003"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {"Data Protection"}

    def test_sub_clauses_preserved(self):
        """The 5 original sub-clauses should be preserved inside the classified entry."""
        clauses = segment_contract(_load_contract("C-003"))
        classified = classify_clauses(clauses)
        dp = classified["Data Protection"]
        assert len(dp.sub_clauses) == 5


class TestClassifierC004:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-004"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {"Payment", "Termination", "Confidentiality"}

    def test_no_automatic_renewal(self):
        """C-004 has no automatic renewal clause — Dataset Note confirms this."""
        clauses = segment_contract(_load_contract("C-004"))
        classified = classify_clauses(clauses)
        assert "Automatic Renewal" not in classified


class TestClassifierC005:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-005"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {
            "Payment", "Automatic Renewal", "Termination",
            "Intellectual Property", "Limitation of Liability",
        }


class TestClassifierC006:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-006"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {
            "Payment", "Termination", "Data Protection", "Limitation of Liability",
        }


class TestClassifierC007:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-007"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {
            "Payment", "Confidentiality", "Intellectual Property", "Limitation of Liability",
        }

    def test_no_termination(self):
        """C-007 has no termination clause — Dataset Note confirms this."""
        clauses = segment_contract(_load_contract("C-007"))
        classified = classify_clauses(clauses)
        assert "Termination" not in classified


class TestClassifierC008:
    def test_categories(self):
        clauses = segment_contract(_load_contract("C-008"))
        classified = classify_clauses(clauses)
        assert set(classified.keys()) == {
            "Payment", "Termination", "Automatic Renewal", "Confidentiality",
        }

    def test_no_limitation_of_liability(self):
        """C-008 has no limitation of liability clause — Dataset Note confirms this."""
        clauses = segment_contract(_load_contract("C-008"))
        classified = classify_clauses(clauses)
        assert "Limitation of Liability" not in classified
