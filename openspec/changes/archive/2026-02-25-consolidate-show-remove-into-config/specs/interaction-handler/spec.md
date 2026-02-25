## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Persistent button interaction system
The bot SHALL handle button interactions using persistent custom_id prefixes that survive bot restarts.

#### Scenario: Button click after restart
- **WHEN** a user clicks a button on a message sent before a bot restart
- **THEN** the bot SHALL correctly identify and handle the interaction based on the custom_id prefix

#### Scenario: Custom_id format differentiation
- **WHEN** a button interaction is received
- **THEN** the bot SHALL distinguish between LeetCode buttons (`{PREFIX}_{problem_id}_{domain}`), external source buttons (`{PREFIX}|{source}|{problem_id}`), and config reset buttons (`config_reset_confirm|...` / `config_reset_cancel|...`)

## PBT Properties

### Property: Button lifecycle completeness
- **INVARIANT**: Every reset button interaction resolves to exactly one of: confirm-success, cancel-success, non-initiator-reject, expired-reject, or permission-reject
- **FALSIFICATION**: Generate all combinations of (initiator/non-initiator) × (unexpired/expired) × (has-permission/no-permission) × (confirm/cancel); assert each maps to exactly one outcome

### Property: Reset confirm idempotency
- **INVARIANT**: Clicking confirm twice produces the same final state (settings deleted, scheduler cleared)
- **FALSIFICATION**: Replay confirm interaction twice; assert DB empty and scheduler state stable after both

### Property: Cancel is side-effect-free
- **INVARIANT**: Cancel click never modifies DB or scheduler state
- **FALSIFICATION**: Snapshot DB and scheduler before cancel; assert identical after cancel
