# care-coordinator-dashboard Specification Delta

## MODIFIED Requirements

### Requirement: Patient detail view — nudge timeline shows channel

MODIFIED to display which channel (WhatsApp or Web) each message was sent/received on. The system SHALL show the channel on each timeline entry as described in the scenarios below.

#### Scenario: Channel badge shown on timeline entry

Given a coordinator views a patient's nudge campaign timeline
When timeline entries render
Then each message shows a `StatusChip` with the channel label (`WhatsApp` or `Web`)

### Requirement: Send chat link from patient detail

ADDED to allow coordinators to send a magic link directly from the dashboard. The system SHALL send a chat magic link via WhatsApp as described in the scenarios below.

#### Scenario: Coordinator sends chat link

Given a coordinator is viewing a patient's detail page
When they click "Send Chat Link"
Then `POST /api/messaging/request-link` is called with the patient's ID
And a success toast confirms the link was sent to the patient's WhatsApp
