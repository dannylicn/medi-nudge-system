# Spec Delta: nudge-campaigns (make-bot-agentic)

## MODIFIED Requirements

### Requirement: Agentic inbound message handling
Inbound Telegram messages from active (non-onboarding) patients MUST be processed by an LLM agent when `OPENAI_API_KEY` or `LLM_BASE_URL` is configured. The agent operates a tool-calling loop capped at 3 iterations per turn. When no LLM key is available, the system MUST fall back to the existing rule-based `classify_response()` path — preserving full functionality without an API key.

**Replaces:** "Response classification" (regex keyword matching as primary path)

#### Scenario: Natural-language adherence confirmation
Given a patient has an open NudgeCampaign with status "sent"
And the patient sends "yeah lah I already took already"
When the agent processes the message
Then the agent MUST call `confirm_adherence` to resolve the campaign
And the campaign status MUST become "resolved"
And the patient MUST receive a positive acknowledgement

#### Scenario: Singlish side effect report
Given a patient sends "eh my chest feel very tight after taking the pill leh"
When the agent processes the message
Then the agent MUST call `escalate` with reason "side_effect" and priority "urgent"
And the patient MUST receive the safety acknowledgement message in their language

#### Scenario: Freeform question about refill
Given a patient with an active PatientMedication sends "when do I need to collect my medicine again?"
When the agent processes the message
Then the agent MUST call `send_reply` with the next refill due date
And NO EscalationCase MUST be created (bot answered the question directly)

#### Scenario: Truly ambiguous message escalated
Given a patient sends a message the agent cannot confidently handle with its available tools
When the agent reaches the 3-iteration limit without a terminal action
Then the system MUST create an EscalationCase with reason "agent_limit_exceeded"
And the patient MUST receive the question acknowledgement message

#### Scenario: LLM unavailable — rule-based fallback activated
Given `OPENAI_API_KEY` is empty and `LLM_BASE_URL` is empty
When any inbound message is received
Then the system MUST use `classify_response()` and existing branch logic
And the behaviour MUST be identical to the pre-agent implementation

### Requirement: Agent context window
Before invoking the LLM, the system MUST compile a context object containing:
- Patient name, language, conditions, onboarding_state, is_active flag
- Active NudgeCampaign (if any): medication name, days_overdue, attempt_number, campaign_id
- Last 5 OutboundMessages bodies (for conversational continuity)

The context MUST NOT include NRIC hash, raw phone number, or any PII beyond name and language.

#### Scenario: Context populated for open campaign
Given a patient has a NudgeCampaign with status "sent" for Metformin, 5 days overdue
When the agent context is built
Then the context MUST include `active_campaign: {medication: "Metformin", days_overdue: 5}`

#### Scenario: Context excludes PII
Given a patient record with nric_hash and phone_number populated
When the agent context is serialised for the LLM prompt
Then the serialised context MUST NOT contain nric_hash
And MUST NOT contain the raw phone_number value

### Requirement: Agent tool guards
Each tool MUST enforce its own preconditions before execution and raise a guarded error if preconditions are not met.

#### Scenario: confirm_adherence requires open campaign
Given no open NudgeCampaign exists for the patient
When the agent calls `confirm_adherence`
Then the tool MUST return an error observation
And the agent MUST NOT change any campaign status

#### Scenario: advance_onboarding restricted to valid states
Given the agent calls `advance_onboarding` with `new_state = "complete"`
When "complete" is not in `ONBOARDING_STATES`
Then the tool MUST return an error observation and take no action
