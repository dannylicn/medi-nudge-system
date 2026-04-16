## 1. Data model and migration
- [ ] 1.1 Create `DoseLog` model: `id`, `patient_id` (FK), `medication_id` (FK), `patient_medication_id` (FK, nullable), `status` (taken/missed/skipped), `source` (patient_reply/campaign_confirmed/caregiver/system_detected), `logged_at` (DateTime), `created_at`
- [ ] 1.2 Add `DoseLogOut` Pydantic schema
- [ ] 1.3 Create Alembic migration for `dose_logs` table

## 2. Logging dose events
- [ ] 2.1 Modify `_handle_taken()` in webhook.py — create DoseLog records for each active med
- [ ] 2.2 Modify `_tool_confirm_adherence()` in agent_service.py — create DoseLog for the campaign's medication
- [ ] 2.3 Modify `_send_due_reminders()` in daily_reminder_service.py — create DoseLog with status=missed when miss is detected
- [ ] 2.4 Create helper `app/services/dose_log_service.py` with `log_dose(db, patient_id, medication_id, status, source)` to centralise logging

## 3. API endpoints
- [ ] 3.1 Add `GET /api/patients/{id}/dose-history` — returns DoseLog list with optional `days` and `medication_id` filters
- [ ] 3.2 Add `GET /api/analytics/dose-adherence` — weekly adherence rate with optional `group_by=medication`

## 4. Frontend — patient detail
- [ ] 4.1 Add API client function `getDoseHistory(patientId, params)`
- [ ] 4.2 Add dose history timeline section to PatientDetailPage — shows last 30 days, missed doses highlighted

## 5. Frontend — analytics
- [ ] 5.1 Add API client functions `getDoseAdherence(params)`
- [ ] 5.2 Add weekly dose adherence line chart to AnalyticsPage
- [ ] 5.3 Add per-medication adherence table to AnalyticsPage (sorted worst-first)

## 6. Tests
- [ ] 6.1 Unit tests for dose_log_service.py
- [ ] 6.2 Integration tests for dose history endpoint
- [ ] 6.3 Integration tests for dose adherence analytics endpoint
- [ ] 6.4 Test that _handle_taken creates DoseLog records
- [ ] 6.5 Test that missed dose detection creates DoseLog records
