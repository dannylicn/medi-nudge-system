# patient-messaging-client Specification Delta

## ADDED Requirements

### Requirement: Patient web chat with magic-link authentication

Patients access a web-based chat interface via a signed magic link sent to their WhatsApp. The link contains a JWT scoped to a single patient with a 24-hour expiry. The system SHALL implement this as described in the scenarios below.

#### Scenario: Magic link requested by coordinator

Given a coordinator clicks "Send Chat Link" on a patient's detail page
When `POST /api/messaging/request-link` is called with `patient_id`
Then a JWT is generated with `sub: <patient_id>`, `purpose: chat`, and 24-hour expiry
And a WhatsApp message containing the link `{FRONTEND_URL}/chat/{token}` is sent to the patient

#### Scenario: Patient opens valid magic link

Given a patient navigates to `/chat/{token}` with a valid, non-expired token
When the chat page loads
Then the patient's display name and greeting are shown
And their message history (across all channels) is displayed in chronological order

#### Scenario: Expired magic link — access denied

Given a patient navigates to `/chat/{token}` with an expired token
When the chat page attempts to fetch messages
Then a `401 Unauthorized` response is returned
And the UI shows "This link has expired. Please request a new link from your care team."

#### Scenario: Tampered token — access denied

Given a token has been modified after signing
When the backend validates the token
Then verification fails and a `401 Unauthorized` response is returned

---

### Requirement: Message history retrieval

The patient can view their full message history — both system-sent nudges and their own replies — across all channels (WhatsApp and Web). The system SHALL implement this as described in the scenarios below.

#### Scenario: Full history loaded on page open

Given a patient opens the chat page
When messages are fetched via `GET /api/messaging/{token}/messages`
Then all `OutboundMessage` records for that patient are returned, sorted by `sent_at` ascending
And each message includes: content, sender (system or patient), channel (whatsapp or web), and timestamp

#### Scenario: Polling for new messages

Given the chat page is open
When the client polls `GET /api/messaging/{token}/messages?after={last_id}` every 5 seconds
Then only messages with `id > last_id` are returned
And new messages are appended to the chat and the view auto-scrolls

#### Scenario: No cross-patient data leakage

Given patient A's token is used to request messages
When the backend queries the database
Then only messages where `patient_id` matches the token's `sub` claim are returned

---

### Requirement: Patient reply via web chat

Patients can send text replies through the web chat. Replies follow the same processing pipeline as WhatsApp inbound messages. The system SHALL implement this as described in the scenarios below.

#### Scenario: Patient sends a reply

Given a patient types a message and taps Send
When `POST /api/messaging/{token}/reply` is called with `{ message: "yes I took it" }`
Then the message is stored with `channel: "web"`
And it is routed through `ResponseClassifier`
And the active `NudgeCampaign` state is updated (same logic as WhatsApp inbound)

#### Scenario: Side effect keyword triggers escalation

Given a patient sends "SIDE EFFECT" via web chat
When the `ResponseClassifier` processes the message
Then an `EscalationCase` is created with the same priority and logic as the WhatsApp path

#### Scenario: No active campaign — reply stored only

Given a patient sends a message but has no active `NudgeCampaign`
When the reply is processed
Then the message is stored for history
And no campaign state transition occurs

---

### Requirement: Mobile-first chat UI with Clinical Serenity design

The patient chat page is a standalone, mobile-first interface using the Clinical Serenity design system. It does not include the coordinator sidebar or navigation. The system SHALL implement this as described in the scenarios below.

#### Scenario: Chat page renders on mobile viewport

Given a patient opens the chat link on a mobile browser
When the page renders
Then the chat fills the full viewport with a fixed header (patient name) and fixed input bar at the bottom
And message bubbles use the `MessagingBubble` component: patient replies in `secondary-container`, system messages in `surface-container-highest`

#### Scenario: Chat page renders on desktop

Given a patient opens the chat link on a desktop browser
When the page renders
Then the chat is centered with `max-w-lg` and the same mobile-first layout scales gracefully
