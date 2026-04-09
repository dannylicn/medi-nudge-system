# whatsapp-channel Specification Delta

## MODIFIED Requirements

### Requirement: Outbound text message via Twilio

MODIFIED to add a `channel` column to `OutboundMessage` distinguishing the originating channel. The system SHALL tag every outbound message with its originating channel as described in the scenarios below.

#### Scenario: Channel field set to whatsapp for Twilio messages

Given a nudge is dispatched via `whatsapp_service.send_text()`
When the `OutboundMessage` record is created
Then `channel` is set to `"whatsapp"`

#### Scenario: Existing messages default to whatsapp

Given existing `OutboundMessage` rows created before the `channel` column was added
When the Alembic migration runs
Then all existing rows have `channel` backfilled to `"whatsapp"`
