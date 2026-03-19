# interaction-handler Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Persistent button interaction system
The bot SHALL handle button interactions using persistent custom_id prefixes that survive bot restarts.

#### Scenario: Button click after restart
- **WHEN** a user clicks a button on a message sent before a bot restart
- **THEN** the bot SHALL correctly identify and handle the interaction based on the custom_id prefix

#### Scenario: Custom_id format differentiation
- **WHEN** a button interaction is received
- **THEN** the bot SHALL distinguish between unified problem buttons (`problem|{source}|{problem_id}|{action}`) and config reset buttons (`config_reset_confirm|...` / `config_reset_cancel|...`)

### Requirement: Problem description button
The bot SHALL display the full problem description when the description button is clicked.

#### Scenario: Show problem description
- **WHEN** a user clicks the problem description button
- **THEN** the bot SHALL fetch the problem content and send it as an ephemeral message

#### Scenario: Content truncation
- **WHEN** the problem description exceeds Discord limits
- **THEN** the bot SHALL truncate at 4000 characters for embeds or 1900 characters for direct messages

### Requirement: LLM translation button
The bot SHALL provide problem translation via LLM when the translation button is clicked.

#### Scenario: Successful translation
- **WHEN** a user clicks the translation button and LLM is configured
- **THEN** the bot SHALL defer the response, fetch or retrieve cached translation, and send it as an ephemeral message

#### Scenario: Cached translation
- **WHEN** a translation for the problem already exists in the cache
- **THEN** the bot SHALL return the cached translation without calling the LLM API

### Requirement: LLM inspiration button
The bot SHALL provide problem-solving inspiration via LLM when the inspiration button is clicked.

#### Scenario: Successful inspiration
- **WHEN** a user clicks the inspiration button and LLM is configured
- **THEN** the bot SHALL defer the response, fetch or retrieve cached inspiration, and send it as an ephemeral message

#### Scenario: Cached inspiration
- **WHEN** inspiration for the problem already exists in the cache
- **THEN** the bot SHALL return the cached inspiration without calling the LLM API

### Requirement: Duplicate request prevention
The bot SHALL prevent duplicate concurrent LLM requests for the same (user_id, problem_id, request_type) tuple using asyncio.Lock.

#### Scenario: Concurrent duplicate request
- **WHEN** a user clicks the same LLM button while a previous request is still processing
- **THEN** the bot SHALL respond with a message indicating the request is already in progress

### Requirement: Submission navigation
The bot SHALL support paginated navigation through user submissions with a 5-minute cache TTL.

#### Scenario: Navigate submissions
- **WHEN** a user clicks the previous/next submission button
- **THEN** the bot SHALL display the corresponding submission page from the cached submissions

#### Scenario: Submission cache expiration
- **WHEN** the cached submission data is older than 5 minutes
- **THEN** the bot SHALL re-fetch submissions from the API

### Requirement: Unified problem action buttons
The bot SHALL handle `view`, `desc`, `translate`, `inspire`, and `similar` actions for problems from all supported sources using the unified problem button format, including buttons rendered from problem overviews and similar-result responses.

#### Scenario: Unified problem action routing
- **WHEN** a user clicks a button with custom_id `problem|{source}|{problem_id}|{action}`
- **THEN** the bot SHALL parse `source`, `problem_id`, and `action` from the custom_id and route the interaction to the matching problem handler

#### Scenario: Overview detail button opens full problem card
- **WHEN** a user clicks an overview detail button with action `view`
- **THEN** the bot SHALL fetch the problem and send the full problem card with its interactive problem view instead of a description-only response

#### Scenario: Similar-result detail button opens full problem card
- **WHEN** a user clicks a similar-result detail button with action `view`
- **THEN** the bot SHALL fetch the problem and send the full problem card with its interactive problem view instead of a description-only response

### Requirement: Legacy problem button compatibility
The bot SHALL preserve compatibility for legacy Discord problem button `custom_id` formats from persisted messages while continuing to generate and prefer the unified problem button format for new messages.

#### Scenario: Legacy problem detail button opens full problem card
- **WHEN** a user clicks a legacy button with custom_id `problem_detail_{problem_id}_{domain}`
- **THEN** the bot SHALL route it to the `view` problem action flow and send the full problem card with its interactive problem view

#### Scenario: Legacy LeetCode problem button shows description
- **WHEN** a user clicks a legacy button with custom_id `leetcode_problem_{problem_id}_{domain}`
- **THEN** the bot SHALL route it to the `desc` problem action flow and send the problem description response

#### Scenario: Legacy LeetCode LLM buttons reuse unified handlers
- **WHEN** a user clicks a legacy button with custom_id `leetcode_translate_{problem_id}_{domain}`, `leetcode_inspire_{problem_id}_{domain}`, or `leetcode_similar_{problem_id}_{domain}`
- **THEN** the bot SHALL route it to the matching `translate`, `inspire`, or `similar` unified problem action flow

#### Scenario: Malformed legacy problem button remains ignored
- **WHEN** a legacy-looking problem button custom_id does not match a supported compatibility pattern
- **THEN** the bot SHALL ignore it without misrouting it to another handler

## PBT Properties

### Property: View-button protocol round-trip
- **INVARIANT**: Every similar-result detail button that reaches the interaction handler can be parsed as `(source, problem_id, view)` without ambiguity
- **FALSIFICATION**: Generate valid and invalid `problem|...|...|view` custom_ids and assert that only valid ids route to the full-card handler

### Property: Stateless full-card routing
- **INVARIANT**: Clicking a similar-result detail button always reuses the existing `view` handler and does not require a separate similar-result interaction state store
- **FALSIFICATION**: Simulate clicks on similar-result detail buttons and assert the handler reaches the same full-card response path used by overview detail buttons

### Requirement: Interaction error handling
The bot SHALL handle interaction errors gracefully with fallback mechanisms.

#### Scenario: Already responded interaction
- **WHEN** an InteractionResponded exception occurs
- **THEN** the bot SHALL fall back to `followup.send()` instead of crashing

### Requirement: Config reset button handler
The `InteractionHandlerCog` SHALL handle reset confirmation and cancellation buttons using persistent `custom_id` routing, surviving bot restarts.

#### Scenario: Confirm reset — valid initiator, unexpired
- **WHEN** the original initiator clicks the "確認重置" button within 180 seconds
- **THEN** the bot SHALL call `delete_server_settings(guild_id)`, call `_reschedule_if_available(guild_id)`, and edit the original message to "✅ 已重置所有設定並停止排程。" with all buttons disabled

#### Scenario: Cancel reset — valid initiator, unexpired
- **WHEN** the original initiator clicks the "取消" button within 180 seconds
- **THEN** the bot SHALL edit the original message to "已取消重置操作。" with all buttons disabled, without modifying DB or scheduler

#### Scenario: Non-initiator click
- **WHEN** a user other than the original initiator clicks either button
- **THEN** the bot SHALL respond with ephemeral text: "此操作僅限原發起者使用。" and take no other action

#### Scenario: Expired button click
- **WHEN** any user clicks either button after 180 seconds from creation
- **THEN** the bot SHALL respond with ephemeral text: "此確認已過期，請重新使用 `/config reset:True`。" and take no other action

#### Scenario: Double confirm click (idempotency)
- **WHEN** the initiator clicks "確認重置" a second time (e.g., due to client retry)
- **THEN** the bot SHALL treat it as idempotent — if settings are already deleted, edit message to the success text with buttons disabled

#### Scenario: Custom_id format
- **WHEN** a reset confirmation button is created
- **THEN** the `custom_id` SHALL follow the format `config_reset_confirm|{guild_id}|{user_id}|{exp_unix}` for confirm and `config_reset_cancel|{guild_id}|{user_id}|{exp_unix}` for cancel

#### Scenario: Permission re-check on confirm
- **WHEN** the initiator clicks "確認重置" but no longer has `manage_guild` permission
- **THEN** the bot SHALL respond with ephemeral text: "您需要「管理伺服器」權限才能執行此操作。" and take no other action

#### Scenario: Custom_id prefix routing
- **WHEN** a button interaction with `custom_id` starting with `config_reset_confirm|` or `config_reset_cancel|` is received
- **THEN** the `InteractionHandlerCog.on_interaction` handler SHALL route it to the reset handler logic

