## MODIFIED Requirements

### Requirement: Reminder times auto-populated from OCR frequency field

> **Modification:** When a `PatientMedication` record is created from an OCR-confirmed scan that includes a frequency field, `PatientMedication.reminder_times` MUST be pre-populated from the parsed frequency before the patient is asked to confirm.

This replaces the prior behaviour where `reminder_times` was always left empty at creation and populated only if the patient explicitly configured daily reminders.

#### Scenario: Frequency field present — times auto-set

Given a confirmed `PrescriptionScan` with `frequency` field value "twice daily" (confidence >= 0.75)
When the `PatientMedication` record is created
Then `reminder_times` is set to `["08:00", "20:00"]`
And the daily reminder scheduler will use these times for this patient-medication pair

#### Scenario: Frequency field absent or low confidence — times remain empty

Given a confirmed `PrescriptionScan` where the `frequency` field has confidence < 0.75 or is absent
When the `PatientMedication` record is created
Then `reminder_times` remains `[]`
And the patient is prompted separately to configure their reminder times
