## MODIFIED Requirements

### Requirement: Side-effect check-in campaign fires 3 days after new medication activation

When a new `PatientMedication` is activated (set to `is_active = True`), the system SHALL create a one-time `side_effect_checkin` nudge campaign that fires approximately 3 days later.

The `NudgeCampaign` model gains a `campaign_type` field. All existing campaigns have `campaign_type = "refill_reminder"` (default). The new type is `"side_effect_checkin"`.

#### Scenario: Check-in created 3 days after activation

Given `PatientMedication` for patient `P-001` / `Metformin` was activated on `2026-04-15`
And patient `P-001` has `onboarding_state = "complete"`
When the daily check-in job runs on `2026-04-18`
And no prior `side_effect_checkin` campaign exists for this patient-medication pair
Then a `NudgeCampaign(campaign_type="side_effect_checkin", status="pending")` is created
And the bot sends: "Hi {name} 👋 You started Metformin a few days ago. How are you getting on? Reply OK — all good, or SIDE EFFECT — feeling unwell."

#### Scenario: Check-in not duplicated

Given a `NudgeCampaign(campaign_type="side_effect_checkin")` already exists for patient `P-001` / `Metformin`
When the daily job runs
Then no additional check-in campaign is created for this pair regardless of prior campaign status

#### Scenario: Patient replies OK to check-in

Given a `NudgeCampaign(campaign_type="side_effect_checkin", status="sent")` exists for patient `P-001`
When the patient replies "OK" or "all good" or equivalent
Then `NudgeCampaign.status` transitions to `resolved`
And a `DoseLog(status="no_issue", source="checkin_ok")` is created for the medication
And no escalation is created

#### Scenario: Patient replies SIDE EFFECT to check-in

Given a `NudgeCampaign(campaign_type="side_effect_checkin", status="sent")` exists for patient `P-001`
When the patient replies "SIDE EFFECT" or describes symptoms
Then the existing `escalate(reason="side_effect", priority="urgent")` flow is triggered
And the safety acknowledgement message is sent to the patient
And `NudgeCampaign.status` transitions to `escalated`

#### Scenario: Check-in not sent during onboarding

Given patient `P-001` has `onboarding_state = "medication_capture"` (not complete)
When the daily job evaluates a `PatientMedication` for `P-001` that was activated 3 days ago
Then no check-in campaign is created
And the check-in is deferred until `onboarding_state = "complete"`
