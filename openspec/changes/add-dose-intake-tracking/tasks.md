## 1. Data model and migration
- [x] 1.1 Create `DoseLog` model: `id`, `patient_id` (FK), `medication_id` (FK), `patient_medication_id` (FK, nullable), `status` (taken/missed/skipped), `source` (patient_reply/campaign_confirmed/caregiver/system_detected), `logged_at` (DateTime), `created_at`
- [x] 1.2 Add `DoseLogOut` Pydantic schema
- [x] 1.3 Create Alembic migration for `dose_logs` table

## 2. Logging dose events
- [x] 2.1 Modify `_handle_taken()` in webhook.py — create DoseLog records for each active med
- [x] 2.2 Modify `_tool_confirm_adherence()` in agent_service.py — create DoseLog for the campaign's medication
- [x] 2.3 Modify `_send_due_reminders()` in daily_reminder_service.py — create DoseLog with status=missed when miss is detected
- [x] 2.4 Create helper `app/services/dose_log_service.py` with `log_dose(db, patient_id, medication_id, status, source)` to centralise logging

## 3. API endpoints
- [x] 3.1 Add `GET /api/patients/{id}/dose-history` — returns DoseLog list with optional `days` and `medication_id` filters
- [x] 3.2 Add `GET /api/analytics/dose-adherence` — weekly adherence rate with optional `group_by=medication`

## 4. Frontend — patient detail
- [x] 4.1 Add API client function `getDoseHistory(patientId, params)`
- [x] 4.2 Add dose history timeline section to PatientDetailPage — shows last 30 days, missed doses highlighted

## 5. Frontend — analytics
- [x] 5.1 Add API client functions `getDoseAdherence(params)`
- [x] 5.2 Add weekly dose adherence line chart to AnalyticsPage
- [x] 5.3 Add per-medication adherence table to AnalyticsPage (sorted worst-first)

## 6. Tests
- [x] 6.1 Unit tests for dose_log_service.py
- [x] 6.2 Integration tests for dose history endpoint
- [x] 6.3 Integration tests for dose adherence analytics endpoint
- [x] 6.4 Test that _handle_taken creates DoseLog records
- [x] 6.5 Test that missed dose detection creates DoseLog records
