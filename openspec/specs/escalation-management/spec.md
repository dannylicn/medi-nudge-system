# escalation-management Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: EscalationCase state machine

An `EscalationCase` progresses through a defined set of states. The system SHALL implement this as described in the scenarios below.

```
open → in_progress → resolved
```

#### Scenario: Case moves to in_progress when coordinator picks it up

Given an `EscalationCase` in `open` state
When a coordinator updates the case with `status: in_progress` and an assignee
Then the case status transitions to `in_progress`

#### Scenario: Case resolved

Given an `EscalationCase` in `in_progress` state
When a coordinator updates the case with `status: resolved` and resolution notes
Then the case transitions to `resolved`
And `resolved_at` timestamp is recorded

#### Scenario: Invalid transition rejected

Given an `EscalationCase` in `resolved` state
When code attempts to transition it to `open`
Then the state machine rejects the transition
And the status remains `resolved`

---

### Requirement: Escalation created for no_response after max attempts

See REQ-NC-005 for the trigger. The escalation service creates the case with the correct parameters. The system SHALL implement this as described in the scenarios below.

#### Scenario: No-response escalation created

Given `MAX_NUDGE_ATTEMPTS = 3` and a campaign has exhausted all three attempts without a confirmed response
When the escalation service is invoked
Then an `EscalationCase` is created with:
  - `reason: no_response`
  - `priority: high`
  - `status: open`
  - `nudge_campaign_id` linking to the campaign

---

### Requirement: Escalation created for side effect reports — always urgent

When a patient reports a side effect, an `EscalationCase` MUST always be created immediately with `priority: urgent`. This MUST never be silently dropped.

#### Scenario: Side effect triggers urgent case

Given a patient's inbound reply is classified as `side_effect`
When the escalation service is invoked
Then an `EscalationCase` is created with `priority: urgent` and `reason: side_effect`
And the case is visible at the top of the coordinator escalation queue

#### Scenario: Side effect at 03:00 AM — case still created

Given a side effect report arrives outside business hours
When the escalation service is invoked
Then the case is still created immediately with `priority: urgent`
And no delay or time-window check applies to safety escalations

---

### Requirement: Escalation created for auto-threshold breach

See REQ-MAT-006. The escalation service creates a case regardless of whether a campaign exists. The system SHALL implement this as described in the scenarios below.

#### Scenario: Threshold breach with no prior campaign

Given `days_overdue = 14` and no `NudgeCampaign` exists for this patient-medication pair
When the scheduler detects the breach
Then an `EscalationCase` is created with `reason: repeated_non_adherence`, `priority: high`
And `nudge_campaign_id` is null

---

### Requirement: Escalation created for patient questions

When a patient's reply is classified as `question`, an `EscalationCase` is created for coordinator follow-up. The system SHALL implement this as described in the scenarios below.

#### Scenario: Question escalation created

Given a patient's inbound reply is classified as `question`
When the escalation service is invoked
Then an `EscalationCase` is created with `reason: patient_question`, `priority: normal`

---

### Requirement: Priority levels

| Priority | Use cases | The system SHALL implement this as described in the scenarios below.
|---|---|
| `urgent` | Side effect, post-discharge safety alert |
| `high` | No response after max attempts, auto-threshold breach |
| `normal` | Patient question |
| `low` | Informational notes, routine coordinator follow-up |

#### Scenario: Priority cannot be downgraded from urgent

Given an `EscalationCase` with `priority: urgent`
When a coordinator updates the case
Then `priority` cannot be changed to a lower value
And the `urgent` classification is preserved for audit

---

### Requirement: Coordinator assignment

Cases can be assigned to a named care coordinator. Unassigned cases remain visible to all coordinators. The system SHALL implement this as described in the scenarios below.

#### Scenario: Case assigned to coordinator

Given an open `EscalationCase`
When a coordinator calls `PATCH /api/escalations/{id}` with `assigned_to: "Nurse Tan"`
Then the case is assigned and `assigned_to` is persisted

#### Scenario: Unassigned case visible to all

Given an `EscalationCase` with no `assigned_to`
When any coordinator queries `GET /api/escalations?status=open`
Then the unassigned case appears in the results

---

### Requirement: Escalation list supports filtering

The coordinator dashboard requires efficient filtering of escalation cases. The system SHALL implement this as described in the scenarios below.

#### Scenario: Filter by priority

Given a mix of escalation cases with different priorities
When a coordinator calls `GET /api/escalations?priority=urgent`
Then only urgent cases are returned

#### Scenario: Filter by status

Given open and resolved cases exist
When a coordinator calls `GET /api/escalations?status=open`
Then only open cases are returned, sorted by `priority` descending then `created_at` ascending

