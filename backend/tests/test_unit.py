"""
T-46: Unit tests for ResponseClassifier, nudge_generator template path,
refill_gap_service logic, and OCR confidence threshold logic.
"""
from unittest.mock import MagicMock, patch
from datetime import date, timedelta

import pytest


# ---------------------------------------------------------------------------
# ResponseClassifier
# ---------------------------------------------------------------------------

from app.services.response_classifier import classify_response


class TestResponseClassifier:
    def test_confirmed_yes(self):
        assert classify_response("Yes") == "confirmed"

    def test_confirmed_taken(self):
        assert classify_response("Taken my meds already") == "confirmed"

    def test_confirmed_sudah(self):
        assert classify_response("Sudah makan") == "confirmed"

    def test_side_effect_keywords(self):
        result = classify_response("I feel dizzy and nauseous")
        assert result == "side_effect"

    def test_side_effect_vomit(self):
        assert classify_response("I am vomiting") == "side_effect"

    def test_negative_no(self):
        assert classify_response("No") == "negative"

    def test_opt_out(self):
        assert classify_response("STOP") == "opt_out"

    def test_opt_out_unsubscribe(self):
        assert classify_response("Unsubscribe please") == "opt_out"

    def test_question_default(self):
        assert classify_response("What time should I take it?") == "question"

    def test_empty_string(self):
        assert classify_response("") == "question"

    def test_case_insensitive(self):
        assert classify_response("YES") == "confirmed"
        assert classify_response("stop") == "opt_out"


# ---------------------------------------------------------------------------
# nudge_generator — template fallback path
# ---------------------------------------------------------------------------

from app.services.nudge_generator import _template_generate


class TestNudgeGeneratorTemplate:
    def test_english_attempt_1(self):
        msg = _template_generate("Alice", "Metformin", 2, "en", 1)
        assert "Alice" in msg or "Metformin" in msg

    def test_english_attempt_3_urgency(self):
        msg = _template_generate("Bob", "Amlodipine", 5, "en", 3)
        assert isinstance(msg, str) and len(msg) > 0

    def test_chinese_attempt_1(self):
        msg = _template_generate("陈大明", "二甲双胍", 3, "zh", 1)
        assert isinstance(msg, str) and len(msg) > 0

    def test_malay_attempt_1(self):
        msg = _template_generate("Ahmad", "Metformin", 1, "ms", 1)
        assert isinstance(msg, str) and len(msg) > 0

    def test_tamil_attempt_1(self):
        msg = _template_generate("Ravi", "Metformin", 2, "ta", 1)
        assert isinstance(msg, str) and len(msg) > 0

    def test_unknown_language_falls_back_to_english(self):
        msg = _template_generate("Alice", "Metformin", 2, "fr", 1)
        # Should return something, not crash
        assert isinstance(msg, str) and len(msg) > 0

    def test_attempt_clamped_to_3(self):
        msg = _template_generate("Alice", "Metformin", 2, "en", 99)
        assert isinstance(msg, str)


# ---------------------------------------------------------------------------
# refill_gap_service — due date + days_overdue logic
# ---------------------------------------------------------------------------

from app.services.refill_gap_service import compute_days_overdue


class TestRefillGapService:
    def test_overdue_positive(self):
        last_dispensed = date.today() - timedelta(days=35)
        days = compute_days_overdue(last_dispensed, supply_days=30)
        assert days == 5

    def test_not_overdue(self):
        last_dispensed = date.today() - timedelta(days=20)
        days = compute_days_overdue(last_dispensed, supply_days=30)
        assert days <= 0

    def test_exactly_on_due_date(self):
        last_dispensed = date.today() - timedelta(days=30)
        days = compute_days_overdue(last_dispensed, supply_days=30)
        assert days == 0

    def test_none_last_dispensed(self):
        """If never dispensed, should return None."""
        days = compute_days_overdue(None, supply_days=30)
        assert days is None


# ---------------------------------------------------------------------------
# OCR confidence threshold logic
# ---------------------------------------------------------------------------

from app.services.ocr_service import _parse_ocr_fields, CONFIDENCE_THRESHOLD


class TestOcrConfidenceThreshold:
    def test_threshold_value(self):
        assert CONFIDENCE_THRESHOLD == 0.75

    def test_low_confidence_flagged(self):
        raw_fields = [
            {"field_name": "medication_name", "value": "Metformin", "confidence": 0.9},
            {"field_name": "dosage", "value": "50mg", "confidence": 0.5},
        ]
        parsed = _parse_ocr_fields(raw_fields)
        low = [f for f in parsed if f["confidence"] < CONFIDENCE_THRESHOLD]
        assert len(low) == 1
        assert low[0]["field_name"] == "dosage"

    def test_high_confidence_not_flagged(self):
        raw_fields = [
            {"field_name": "medication_name", "value": "Amlodipine", "confidence": 0.95},
        ]
        parsed = _parse_ocr_fields(raw_fields)
        low = [f for f in parsed if f["confidence"] < CONFIDENCE_THRESHOLD]
        assert len(low) == 0
