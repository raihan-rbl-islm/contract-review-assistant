"""
Tests for the clause segmenter.
Asserts correct clause count and headings for all 8 contracts.
See Plan.md §5.
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.segmenter import segment_contract


# Load all contract texts once for the test module
_CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "problem Datasets" / "contracts"


def _load_contract(contract_id: str) -> str:
    """Load raw contract text by ID."""
    path = _CONTRACTS_DIR / f"{contract_id}.txt"
    return path.read_text(encoding="utf-8")


class TestSegmenterC001:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-001"))
        assert len(clauses) == 4

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-001"))
        headings = [c.heading for c in clauses]
        assert headings == ["Payment", "Termination", "Automatic Renewal", "Limitation of Liability"]

    def test_section_numbers(self):
        clauses = segment_contract(_load_contract("C-001"))
        sections = [c.section_number for c in clauses]
        assert sections == ["2.1", "5.2", "7.1", "9.3"]

    def test_dataset_note_excluded(self):
        clauses = segment_contract(_load_contract("C-001"))
        for clause in clauses:
            assert "Dataset Note" not in clause.text


class TestSegmenterC002:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-002"))
        assert len(clauses) == 4

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-002"))
        headings = [c.heading for c in clauses]
        assert headings == ["Payment", "Termination", "Confidentiality", "Intellectual Property"]


class TestSegmenterC003:
    def test_clause_count(self):
        """C-003 has 5 data-protection sub-clauses with different headings."""
        clauses = segment_contract(_load_contract("C-003"))
        assert len(clauses) == 5

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-003"))
        headings = [c.heading for c in clauses]
        assert headings == [
            "Use of Data", "Security", "Breach Notice",
            "Subprocessors", "Data Return and Deletion",
        ]


class TestSegmenterC004:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-004"))
        assert len(clauses) == 3

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-004"))
        headings = [c.heading for c in clauses]
        assert headings == ["Payment", "Termination", "Confidentiality"]


class TestSegmenterC005:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-005"))
        assert len(clauses) == 5

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-005"))
        headings = [c.heading for c in clauses]
        assert headings == [
            "Payment", "Automatic Renewal", "Termination",
            "Intellectual Property", "Liability",
        ]


class TestSegmenterC006:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-006"))
        assert len(clauses) == 4

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-006"))
        headings = [c.heading for c in clauses]
        assert headings == [
            "Payment", "Termination for Breach",
            "Data Protection", "Limitation of Liability",
        ]


class TestSegmenterC007:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-007"))
        assert len(clauses) == 4

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-007"))
        headings = [c.heading for c in clauses]
        assert headings == [
            "Payment", "Confidentiality",
            "Intellectual Property", "Limitation of Liability",
        ]


class TestSegmenterC008:
    def test_clause_count(self):
        clauses = segment_contract(_load_contract("C-008"))
        assert len(clauses) == 4

    def test_headings(self):
        clauses = segment_contract(_load_contract("C-008"))
        headings = [c.heading for c in clauses]
        assert headings == [
            "Payment", "Termination",
            "Automatic Renewal", "Confidentiality",
        ]
