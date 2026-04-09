# whatsapp-channel Specification

## Purpose
TBD - created by archiving change init-core-platform. Update Purpose after archive.
## Requirements
### Requirement: Outbound text message via Twilio

The system sends WhatsApp text messages through the Twilio WhatsApp Business API. The system SHALL implement this as described in the scenarios below.

#### Scenario: Text nudge dispatched

Given a `NudgeCampaign` with generated `message_content` in `pending` state
When `whatsapp_service.send_text()` is called
Then a Twilio API request is made with the patient's phone number as the recipient
And an `OutboundMessage` record is created with `delivery_mode: text` and `status: sent`
And `OutboundMessage.whatsapp_message_id` is populated with the Twilio message SID

#### Scenario: Twilio API failure — message marked failed

Given the Twilio API returns a 5xx error
When `whatsapp_service.send_text()` catches the exception
Then the `OutboundMessage` status is set to `failed`
And the error is logged with the patient ID and campaign ID (no PII beyond phone number)
And the campaign scheduler will retry according to REQ-NC-005

---

### Requirement: Delivery status tracking via Twilio callback

Twilio posts delivery status updates to a callback endpoint; the system updates `OutboundMessage.status` accordingly. The system SHALL implement this as described in the scenarios below.

```
sent → delivered → read
     └→ failed
```

#### Scenario: Delivery confirmed

Given Twilio sends a status callback with `MessageStatus: delivered` for a known message SID
When `POST /api/webhook/whatsapp/status` is processed
Then `OutboundMessage.status` is updated to `delivered`
And `OutboundMessage.delivered_at` is recorded

#### Scenario: Unknown message SID in callback

Given Twilio sends a callback for a message SID that does not exist in the database
When the endpoint processes the callback
Then a `404` is logged and the webhook returns `200` to Twilio (to prevent Twilio retries)

---

### Requirement: Inbound webhook endpoint with Twilio signature validation

All inbound WhatsApp messages are received via a Twilio webhook. The endpoint MUST validate the `X-Twilio-Signature` HMAC-SHA1 header before processing any message content.

#### Scenario: Valid signature — message processed

Given Twilio sends an inbound message with a valid `X-Twilio-Signature`
When `POST /api/webhook/whatsapp` is received
Then the signature is verified using `TWILIO_AUTH_TOKEN`
And the message body is passed to the `ResponseClassifier`

#### Scenario: Invalid signature — request rejected

Given an HTTP request arrives at `POST /api/webhook/whatsapp` without a valid `X-Twilio-Signature`
When the endpoint validates the signature
Then a `403 Forbidden` response is returned
And no message content is processed or logged

#### Scenario: Missing signature header — request rejected

Given an HTTP request arrives at `POST /api/webhook/whatsapp` with no `X-Twilio-Signature` header
When the endpoint validates the signature
Then a `403 Forbidden` response is returned

---

### Requirement: Response classification

Inbound patient replies are classified into one of four response types using keyword and pattern matching. The system SHALL implement this as described in the scenarios below.

| Classification | Trigger keywords/patterns |
|---|---|
| `confirmed` | `yes`, `ok`, `done`, `collected`, `taken`, `ya`, `好`, `可以` |
| `side_effect` | `side effect`, `pain`, `rash`, `dizzy`, `dizziness`, `unwell`, `sick`, `不舒服`, `痛` |
| `question` | `?`, `how`, `what`, `when`, `can i`, `should i`, `boleh`, `怎么` |
| `negative` | `no`, `cannot`, `stop`, `don't want`, `tak mau`, `不要` |

#### Scenario: Confirmed response classified correctly

Given a patient replies `collected it just now`
When the `ResponseClassifier` processes the message
Then the classification is `confirmed`

#### Scenario: Side effect keyword detected

Given a patient replies `I have a rash since yesterday`
When the `ResponseClassifier` processes the message
Then the classification is `side_effect`

#### Scenario: Unrecognised reply — classified as question

Given a patient sends a message that matches no known keyword
When the `ResponseClassifier` processes the message
Then the classification defaults to `question` (conservative fallback to ensure human review)

#### Scenario: Classification matched to open campaign

Given patient `P-001` has an open `NudgeCampaign` in `sent` state
When an inbound message from `P-001`'s phone number is classified
Then the classification is applied to that campaign
And the campaign state machine is advanced accordingly (see REQ-NC-006, REQ-NC-007, REQ-NC-008)

---

### Requirement: Patient identified by phone number

Inbound messages are matched to patients via `Patient.phone_number` (E.164). The system SHALL implement this as described in the scenarios below.

#### Scenario: Known phone number

Given an inbound WhatsApp message from `+6591234567`
When the webhook handler looks up the sender
Then the patient with `phone_number: +6591234567` is identified
And the message is processed in the context of that patient

#### Scenario: Unknown phone number

Given an inbound message from a phone number not in the system
When the webhook handler looks up the sender
Then the message is logged with the phone number (no patient context)
And a human-readable auto-reply is sent: "We don't recognise this number. Please contact your clinic."
And no patient data is exposed in the reply

---

### Requirement: Outbound message rate limiting and quiet hours

Messages MUST not be sent to a patient outside their configured quiet hours window.

#### Scenario: Message held until contact window

Given patient `P-001` has quiet hours `22:00–08:00` in their time zone
When a nudge is triggered at `23:00`
Then the message is queued and dispatched after `08:00` the next morning

#### Scenario: No quiet hours configured — default window applied

Given a patient has not configured quiet hours
When a nudge is triggered
Then the message is sent immediately (no restriction)

