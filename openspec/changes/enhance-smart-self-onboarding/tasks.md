# Tasks: enhance-smart-self-onboarding

## Phase 1: Data model + migration
- [ ] 1. Add `patient_confirmed` and `patient_pending` to `PrescriptionScan.status` enum; add `campaign_type` column to `NudgeCampaign` with `side_effect_checkin` value; add `ocr_patient_confirmed` to `EscalationCase.reason` enum; add `med_info_card_sent_at` timestamp to `PatientMedication`
- [ ] 2. Write and run Alembic migration for the above changes
- [ ] 3. Update `schemas.py` (Pydantic): add new enum values to response schemas

## Phase 2: OCR fast path
- [ ] 4. Add `_is_high_confidence(scan)` helper to `ocr_service.py`
- [ ] 5. Add `send_ocr_confirmation_prompt(patient, scan, db)` to `onboarding_service.py` — formats and sends extracted fields to patient in their language
- [ ] 6. Update `ocr_service.py` `process_scan()` to branch: high-confidence → patient prompt (status=patient_pending); low-confidence → existing coordinator queue (status=review)
- [ ] 7. Update `webhook.py` to handle `CONFIRM` / `EDIT` replies when patient is in `patient_pending_ocr_confirmation` state
  - CONFIRM → PrescriptionScan status=patient_confirmed + create low-priority coordinator EscalationCase + auto-populate medication records + advance onboarding state to `confirm`
  - EDIT → PrescriptionScan status=review (coordinator queue) + patient state back to `medication_capture`

## Phase 3: Reminder-time auto-setup
- [ ] 8. Add `_parse_frequency_to_times(frequency_text)` to `ocr_service.py` (regex/lookup table, no LLM)
- [ ] 9. In `onboarding_service.py`, after OCR confirmation, call `_parse_frequency_to_times()`, set `PatientMedication.reminder_times`, and send schedule confirmation prompt to patient
- [ ] 10. Handle patient schedule reply (`OK` or custom times) in `webhook.py`; on custom times, attempt LLM parse, fall back to asking coordinator

## Phase 4: Medication info card
- [ ] 11. Create `app/services/medication_info_service.py` with `generate_info_card(medication_name, language, condition=None)` — LLM call + fallback templates + content safety filter
- [ ] 12. Call `medication_info_service.generate_info_card()` after medication is confirmed in onboarding (OCR fast-path, coordinator-confirmed OCR, and manual entry paths); gate on `med_info_card_sent_at IS NULL`
- [ ] 13. Add 60-second delayed send (APScheduler one-shot job) so info card lands after the confirmation ack; set `PatientMedication.med_info_card_sent_at` on send

## Phase 5: Side-effect check-in
- [ ] 14. Create `app/services/side_effect_checkin_service.py` with `run_side_effect_checkin_check(db)` — queries PatientMedication activated 3–4 days ago, creates campaigns
- [ ] 15. Register job in `app/scheduler.py` (daily at 09:05 SGT)
- [ ] 16. Update `nudge_campaign_service.py` to handle `campaign_type == "side_effect_checkin"` in response routing
- [ ] 17. Update `webhook.py` / `agent_service.py`: route `OK` / `SIDE EFFECT` replies when active campaign is `side_effect_checkin` type

## Phase 6: Tests
- [ ] 18. Test `_is_high_confidence()` — boundary cases at 0.84 and 0.85 confidence; missing required field
- [ ] 19. Test OCR fast-path state transition: patient_pending → patient_confirmed → medication records created
- [ ] 20. Test OCR edit path: patient_pending → review (drops to coordinator queue)
- [ ] 21. Test `_parse_frequency_to_times()` — "twice daily", "with meals", "nocte", unknown/None
- [ ] 22. Test `generate_info_card()` — LLM path; fallback path when LLM unavailable; content safety filter (response containing "dosage" → fallback)
- [ ] 23. Test side-effect check-in job: creates campaign exactly 3 days post-activation; does not duplicate; skips patients still in onboarding
- [ ] 24. Test check-in response routing: OK → resolved + DoseLog(status=no_issue); SIDE EFFECT → escalation(urgent)

## Dependencies
- Phase 1 must complete before Phases 2–5 (all depend on new DB columns)
- Phases 2–5 are independent of each other and can be implemented in parallel after Phase 1
- Phase 6 tests should be written alongside implementation (TDD preferred)
