"""
Tests for intent classification.
Asserts all 12 public test questions and 3 missing-info questions resolve
to the correct category. See Plan.md §6a.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.intent import classify_intent


class TestIntentPublicQuestions:
    """All 12 public test questions should resolve to the correct category."""

    def test_pq01_automatic_renewal(self):
        result = classify_intent("Review the automatic renewal clause. What is the risk level and why?")
        assert not result.ambiguous
        assert result.category == "Automatic Renewal"

    def test_pq02_payment(self):
        result = classify_intent("Review the payment clause against the company standard.")
        assert not result.ambiguous
        assert result.category == "Payment"

    def test_pq03_intellectual_property(self):
        result = classify_intent("Who owns the custom work, and does this match the company standard?")
        assert not result.ambiguous
        assert result.category == "Intellectual Property"

    def test_pq04_data_protection(self):
        result = classify_intent("Review the data breach notification time.")
        assert not result.ambiguous
        assert result.category == "Data Protection"

    def test_pq05_data_protection(self):
        result = classify_intent("Does the security clause require encryption of stored data?")
        assert not result.ambiguous
        assert result.category == "Data Protection"

    def test_pq06_termination(self):
        result = classify_intent("Review the termination clause.")
        assert not result.ambiguous
        assert result.category == "Termination"

    def test_pq07_automatic_renewal(self):
        result = classify_intent("Will this contract renew automatically?")
        assert not result.ambiguous
        assert result.category == "Automatic Renewal"

    def test_pq08_intellectual_property(self):
        result = classify_intent("Review the ownership of campaign materials.")
        assert not result.ambiguous
        assert result.category == "Intellectual Property"

    def test_pq09_limitation_of_liability(self):
        result = classify_intent("Review the limitation of liability clause.")
        assert not result.ambiguous
        assert result.category == "Limitation of Liability"

    def test_pq10_termination(self):
        result = classify_intent("Does the termination-for-breach clause provide time to fix a normal breach?")
        assert not result.ambiguous
        assert result.category == "Termination"

    def test_pq11_confidentiality(self):
        result = classify_intent("Review the confidentiality period.")
        assert not result.ambiguous
        assert result.category == "Confidentiality"

    def test_pq12_automatic_renewal(self):
        result = classify_intent("Review the automatic renewal clause.")
        assert not result.ambiguous
        assert result.category == "Automatic Renewal"


class TestIntentMissingInfoCases:
    """All 3 missing-info questions should resolve to the correct category."""

    def test_mi01_automatic_renewal(self):
        result = classify_intent("What notice is required to stop automatic renewal?")
        assert not result.ambiguous
        assert result.category == "Automatic Renewal"

    def test_mi02_termination(self):
        result = classify_intent("Can either party terminate the agreement for convenience?")
        assert not result.ambiguous
        assert result.category == "Termination"

    def test_mi03_limitation_of_liability(self):
        result = classify_intent("What is the total liability cap?")
        assert not result.ambiguous
        assert result.category == "Limitation of Liability"


class TestIntentEdgeCases:
    """Rephrased questions should still resolve correctly (per Plan.md §22 checklist)."""

    def test_rephrased_renewal(self):
        result = classify_intent("Does this agreement renew automatically without notice?")
        assert not result.ambiguous
        assert result.category == "Automatic Renewal"

    def test_rephrased_termination(self):
        result = classify_intent("How can we end the agreement early?")
        assert not result.ambiguous
        assert result.category == "Termination"

    def test_ambiguous_returns_ambiguous(self):
        """A question with no recognizable keywords should return ambiguous."""
        result = classify_intent("What is the weather today?")
        assert result.ambiguous
        assert result.category is None
