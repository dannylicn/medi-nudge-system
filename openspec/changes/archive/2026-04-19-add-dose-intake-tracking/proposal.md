# Change: Add dose intake tracking table and analytics views

## Why

The system currently tracks medication intake with a single `last_taken_at` timestamp and a `consecutive_missed_doses` counter on `PatientMedication`. All historical dose data is lost — there's no way to see when a patient took (or missed) each dose over time. Care coordinators need per-patient dose history and system-wide adherence analytics to identify at-risk patients and measure program effectiveness.

## What Changes

- **New `dose_logs` table**: Records every dose event (taken, missed, skipped) with timestamp, source (patient reply, caregiver confirmation, system-detected miss), and the medication involved.
- **Modified intake handlers**: `_handle_taken()` in webhook.py and `_tool_confirm_adherence()` in agent_service.py now create `DoseLog` records when a patient reports taking their medication.
- **Modified missed dose detection**: `daily_reminder_service.py` creates `DoseLog` records with `status=missed` when a dose window passes without confirmation.
- **New API endpoints**: Per-patient dose history and aggregate adherence analytics (by medication, by time period).
- **Modified frontend**: Dose history timeline on PatientDetailPage; aggregate dose adherence charts on AnalyticsPage.

## Impact

- Affected specs: `medication-adherence-tracking` (modified), `care-coordinator-dashboard` (modified)
- Affected code:
  - New: `app/models/models.py` (DoseLog), migration
  - Modified: `app/routers/webhook.py` (_handle_taken), `app/services/agent_service.py` (_tool_confirm_adherence), `app/services/daily_reminder_service.py` (missed dose logging), `app/routers/analytics.py` (new endpoints), `app/schemas/schemas.py` (DoseLogOut)
  - Frontend: `PatientDetailPage.jsx` (dose timeline), `AnalyticsPage.jsx` (aggregate charts), `api.js` (new endpoints)
