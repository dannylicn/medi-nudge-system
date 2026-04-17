"""Tests for dose intake tracking: logging, history endpoint, analytics."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from app.models.models import Patient, Medication, PatientMedication, DoseLog


def _make_patient(db, phone, chat_id=None):
    p = Patient(
        full_name="Test Patient",
        phone_number=phone,
        telegram_chat_id=chat_id,
        onboarding_state="complete",
        is_active=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_med(db, name, generic):
    m = Medication(name=name, generic_name=generic, default_refill_days=30)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _make_pm(db, patient, med):
    pm = PatientMedication(
        patient_id=patient.id,
        medication_id=med.id,
        is_active=True,
        frequency="once_daily",
    )
    db.add(pm)
    db.commit()
    db.refresh(pm)
    return pm


# ---------------------------------------------------------------------------
# dose_log_service unit tests
# ---------------------------------------------------------------------------

class TestDoseLogService:
    def test_log_dose_creates_record(self, db):
        from app.services.dose_log_service import log_dose

        patient = _make_patient(db, "+6591100001")
        med = _make_med(db, "TestMed", "testmed_log_001")

        entry = log_dose(db, patient.id, med.id, "taken", "patient_reply")

        assert entry.id is not None
        assert entry.status == "taken"
        assert entry.source == "patient_reply"
        assert entry.patient_id == patient.id
        assert entry.medication_id == med.id

    def test_log_dose_with_pm_id(self, db):
        from app.services.dose_log_service import log_dose

        patient = _make_patient(db, "+6591100002")
        med = _make_med(db, "TestMed2", "testmed_log_002")
        pm = _make_pm(db, patient, med)

        entry = log_dose(db, patient.id, med.id, "missed", "system_detected", patient_medication_id=pm.id)

        assert entry.patient_medication_id == pm.id
        assert entry.status == "missed"


# ---------------------------------------------------------------------------
# _handle_taken creates DoseLog records
# ---------------------------------------------------------------------------

class TestHandleTakenDoseLog:
    def test_handle_taken_creates_dose_logs(self, db):
        patient = _make_patient(db, "+6591100003", chat_id="600001")
        med = _make_med(db, "Metformin", "metformin_dl_003")
        _make_pm(db, patient, med)

        with patch("app.services.telegram_service.send_text") as ms:
            ms.return_value = MagicMock(status="sent")
            from app.routers.webhook import _handle_taken
            _handle_taken(db, patient)

        logs = db.query(DoseLog).filter(DoseLog.patient_id == patient.id).all()
        assert len(logs) == 1
        assert logs[0].status == "taken"
        assert logs[0].source == "patient_reply"
        assert logs[0].medication_id == med.id


# ---------------------------------------------------------------------------
# Missed dose detection creates DoseLog records
# ---------------------------------------------------------------------------

class TestMissedDoseDoseLog:
    def test_missed_dose_creates_log(self, db):
        patient = _make_patient(db, "+6591100004", chat_id="600002")
        med = _make_med(db, "Amlodipine", "amlodipine_dl_004")
        pm = _make_pm(db, patient, med)

        # Set last_reminded_at to 5 hours ago (past the 4h grace window)
        pm.last_reminded_at = datetime.utcnow() - timedelta(hours=5)
        pm.last_taken_at = None
        pm.reminder_times = ["08:00"]
        db.commit()

        with patch("app.services.telegram_service.send_text") as ms, \
             patch("app.services.tts_service.generate_voice_message", return_value=None):
            ms.return_value = MagicMock(status="sent")

            from app.services.daily_reminder_service import send_scheduled_reminders
            send_scheduled_reminders(db, skip_window=True)

        logs = db.query(DoseLog).filter(
            DoseLog.patient_id == patient.id,
            DoseLog.status == "missed",
        ).all()
        assert len(logs) >= 1
        assert logs[0].source == "system_detected"


# ---------------------------------------------------------------------------
# Dose history endpoint
# ---------------------------------------------------------------------------

class TestDoseHistoryEndpoint:
    def test_dose_history_returns_records(self, client, auth_headers, db):
        patient = _make_patient(db, "+6591100005")
        med = _make_med(db, "Losartan", "losartan_dl_005")

        from app.services.dose_log_service import log_dose
        log_dose(db, patient.id, med.id, "taken", "patient_reply")
        log_dose(db, patient.id, med.id, "missed", "system_detected")

        resp = client.get(f"/api/patients/{patient.id}/dose-history?days=30", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["medication_name"] == "Losartan"

    def test_dose_history_filter_by_medication(self, client, auth_headers, db):
        patient = _make_patient(db, "+6591100006")
        med1 = _make_med(db, "Med A", "med_a_dl_006")
        med2 = _make_med(db, "Med B", "med_b_dl_006")

        from app.services.dose_log_service import log_dose
        log_dose(db, patient.id, med1.id, "taken", "patient_reply")
        log_dose(db, patient.id, med2.id, "taken", "patient_reply")

        resp = client.get(f"/api/patients/{patient.id}/dose-history?medication_id={med1.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["medication_name"] == "Med A"


# ---------------------------------------------------------------------------
# Dose adherence analytics endpoint
# ---------------------------------------------------------------------------

class TestDoseAdherenceEndpoint:
    def test_weekly_adherence(self, client, auth_headers, db):
        patient = _make_patient(db, "+6591100007")
        med = _make_med(db, "Statin", "statin_dl_007")

        from app.services.dose_log_service import log_dose
        log_dose(db, patient.id, med.id, "taken", "patient_reply")
        log_dose(db, patient.id, med.id, "taken", "patient_reply")
        log_dose(db, patient.id, med.id, "missed", "system_detected")

        resp = client.get("/api/analytics/dose-adherence?days=30", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert "adherence_rate" in data[0]
        assert data[0]["taken"] == 2
        assert data[0]["missed"] == 1

    def test_group_by_medication(self, client, auth_headers, db):
        patient = _make_patient(db, "+6591100008")
        med1 = _make_med(db, "Med X", "med_x_dl_008")
        med2 = _make_med(db, "Med Y", "med_y_dl_008")

        from app.services.dose_log_service import log_dose
        log_dose(db, patient.id, med1.id, "taken", "patient_reply")
        log_dose(db, patient.id, med2.id, "missed", "system_detected")

        resp = client.get("/api/analytics/dose-adherence?days=30&group_by=medication", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Sorted worst-first
        assert data[0]["adherence_rate"] <= data[1]["adherence_rate"]
