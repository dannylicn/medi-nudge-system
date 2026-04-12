"""
Daily medication-taking reminder service.
Sends Telegram reminders to patients based on their per-medication schedule.
Runs every 30 minutes; fires reminders whose scheduled time falls within the current window.
"""
import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session, joinedload
from app.core.database import SessionLocal
from app.models.models import Patient, PatientMedication
from app.services import telegram_service
from app.services.nudge_generator import generate_daily_reminder

logger = logging.getLogger(__name__)
SGT = ZoneInfo("Asia/Singapore")

# Default reminder times by frequency (SGT)
FREQUENCY_DEFAULTS: dict[str, list[str]] = {
    "once_daily":        ["08:00"],
    "twice_daily":       ["08:00", "20:00"],
    "three_times_daily": ["08:00", "13:00", "20:00"],
    "every_other_day":   ["08:00"],
    "weekly":            ["08:00"],
    "as_needed":         [],
}


def _in_window(time_str: str, now_sgt: datetime, window_minutes: int = 14) -> bool:
    """Return True if the HH:MM time falls within ±window_minutes of now (SGT)."""
    try:
        h, m = map(int, time_str.split(":"))
    except ValueError:
        return False
    scheduled = now_sgt.replace(hour=h, minute=m, second=0, microsecond=0)
    delta = abs((now_sgt - scheduled).total_seconds())
    return delta <= window_minutes * 60


def send_scheduled_reminders(db: Session | None = None) -> dict:
    """
    Called every 30 minutes. For each patient medication, check if any
    reminder_time falls within the current 30-minute window and send the nudge.
    Groups all due medications for a patient into a single message.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    now_sgt = datetime.now(SGT)
    results = {"patients_checked": 0, "reminders_sent": 0, "skipped": 0, "errors": 0}

    try:
        patients = (
            db.query(Patient)
            .filter(
                Patient.is_active == True,  # noqa: E712
                Patient.onboarding_state == "complete",
            )
            .all()
        )

        for patient in patients:
            results["patients_checked"] += 1
            try:
                _send_due_reminders(db, patient, now_sgt, results)
            except Exception as exc:
                logger.error("Reminder error for patient %s: %s", patient.id, exc)
                results["errors"] += 1

    finally:
        if owns_session:
            db.close()

    logger.info("Scheduled reminders (%s SGT): %s", now_sgt.strftime("%H:%M"), results)
    return results


def _send_due_reminders(
    db: Session, patient: Patient, now_sgt: datetime, results: dict
) -> None:
    active_meds = (
        db.query(PatientMedication)
        .options(joinedload(PatientMedication.medication))
        .filter(
            PatientMedication.patient_id == patient.id,
            PatientMedication.is_active == True,  # noqa: E712
        )
        .all()
    )

    if not active_meds:
        results["skipped"] += 1
        return

    # Collect medications that are due right now
    due_meds: list[str] = []
    for pm in active_meds:
        times = pm.reminder_times or FREQUENCY_DEFAULTS.get(pm.frequency, [])
        if any(_in_window(t, now_sgt) for t in times):
            med_name = pm.medication.name if pm.medication else f"Medication #{pm.medication_id}"
            dosage_suffix = f" ({pm.dosage})" if pm.dosage else ""
            due_meds.append(f"{med_name}{dosage_suffix}")

    if not due_meds:
        results["skipped"] += 1
        return

    message = generate_daily_reminder(
        name=patient.full_name.split()[0],
        medications=due_meds,
        language=patient.language_preference,
        conditions=patient.conditions,
    )

    telegram_service.send_text(
        db=db,
        patient_id=patient.id,
        to_phone=patient.phone_number,
        body=message,
    )
    results["reminders_sent"] += 1
    logger.debug(
        "Sent reminder to patient %s for: %s (time: %s SGT)",
        patient.id, due_meds, now_sgt.strftime("%H:%M"),
    )
