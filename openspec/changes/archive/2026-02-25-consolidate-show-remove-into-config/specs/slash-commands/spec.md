## MODIFIED Requirements

### Requirement: Unified config command
The `/config` command SHALL allow server admins to view, update, and reset all server configuration. It dispatches three modes based on parameters: **show** (no params), **reset** (`reset:True` alone), and **update** (any setting params).

#### Scenario: Show mode — server has settings
- **WHEN** an admin runs `/config` without any parameters and the server has existing settings
- **THEN** the bot SHALL display the current settings using `create_settings_embed()` as an ephemeral message

#### Scenario: Show mode — server has no settings
- **WHEN** an admin runs `/config` without any parameters and the server has no settings
- **THEN** the bot SHALL respond with ephemeral text: "尚未設定 LeetCode 每日挑戰頻道。使用 `/config channel:<頻道>` 開始設定。"

#### Scenario: Update success response
- **WHEN** any `/config` update succeeds
- **THEN** the bot SHALL respond with `content="✅ 設定已更新"` and an embed from `create_settings_embed()` reflecting the persisted state, as an ephemeral message

#### Scenario: Reset mode — server has settings
- **WHEN** an admin runs `/config reset:True` without other params and the server has existing settings
- **THEN** the bot SHALL send an ephemeral message containing a settings summary embed and two buttons labeled "確認重置" (danger style) and "取消" (secondary style)

#### Scenario: Reset mode — server has no settings
- **WHEN** an admin runs `/config reset:True` and the server has no settings
- **THEN** the bot SHALL respond with ephemeral text: "此伺服器尚未設定，無需重置。"

#### Scenario: Reset mutual exclusion
- **WHEN** an admin runs `/config reset:True` together with any of `channel`, `role`, `time`, `timezone`, or `clear_role`
- **THEN** the bot SHALL reject with ephemeral text: "`reset` 不可與其他設定參數同時使用。"

#### Scenario: Mode dispatch order
- **WHEN** `/config` is invoked
- **THEN** the bot SHALL evaluate in order: reset conflict check → show mode check → input validation → update logic

#### Scenario: First-time setup with all parameters
- **WHEN** an admin with `manage_guild` permission runs `/config channel:#general time:08:00 timezone:UTC+8`
- **THEN** the bot SHALL save all settings and trigger schedule creation, responding with `content="✅ 設定已更新"` and a settings embed

#### Scenario: Partial update
- **WHEN** an admin runs `/config time:09:00` on a server with existing settings
- **THEN** the bot SHALL update only `post_time` to `09:00`, preserving all other settings, and trigger reschedule

#### Scenario: First-time setup without channel
- **WHEN** an admin runs `/config time:08:00` on a server with no existing settings
- **THEN** the bot SHALL respond with an ephemeral error stating channel is required for first-time setup, with usage example

#### Scenario: Atomic validation failure
- **WHEN** an admin runs `/config time:08:00 timezone:InvalidZone`
- **THEN** the bot SHALL reject the entire request without updating any field, returning the timezone validation error

#### Scenario: Permission check
- **WHEN** a user without `manage_guild` permission runs `/config`
- **THEN** the bot SHALL respond with ephemeral text: "您需要「管理伺服器」權限才能使用此指令。"

#### Scenario: Guild-only enforcement
- **WHEN** a user runs `/config` in a DM
- **THEN** the bot SHALL respond indicating this command cannot be used in DMs

#### Scenario: Reset parameter describe text
- **WHEN** the `reset` parameter is displayed in Discord's command UI
- **THEN** the describe text SHALL be "重置所有設定並停止排程（需確認）"

### Requirement: Role clearing via config command
The `/config` command SHALL support clearing the notification role via a `clear_role` boolean parameter.

#### Scenario: Clear existing role
- **WHEN** an admin runs `/config clear_role:True` on a server with a role set
- **THEN** the bot SHALL set `role_id` to NULL in the database and display "未設定" for role in the success response

#### Scenario: Clear role with simultaneous role parameter
- **WHEN** an admin runs `/config role:@SomeRole clear_role:True`
- **THEN** the bot SHALL reject with an ephemeral error indicating `role` and `clear_role` are mutually exclusive

#### Scenario: Clear role when no role set
- **WHEN** an admin runs `/config clear_role:True` on a server with no role configured
- **THEN** the bot SHALL succeed without error (idempotent), keeping role as NULL

### Requirement: Time format auto-padding
The `/config` command SHALL accept single-digit hour format and normalize to zero-padded `HH:MM` before storage.

#### Scenario: Single-digit hour normalization
- **WHEN** an admin runs `/config time:8:00`
- **THEN** the bot SHALL store `08:00` in the database

#### Scenario: Already padded time
- **WHEN** an admin runs `/config time:08:00`
- **THEN** the bot SHALL store `08:00` in the database (no change)

#### Scenario: Invalid time rejection
- **WHEN** an admin runs `/config time:24:00` or `/config time:12:60`
- **THEN** the bot SHALL reject with an ephemeral error showing valid format examples

### Requirement: Timezone autocomplete
The `/config` command SHALL provide autocomplete suggestions for the `timezone` parameter.

#### Scenario: Empty input autocomplete
- **WHEN** the user opens the timezone autocomplete without typing
- **THEN** the bot SHALL show popular options including `UTC`, common UTC offsets (UTC+8, UTC+9, UTC-5, etc.), and popular IANA zones (Asia/Taipei, Asia/Tokyo, America/New_York, Europe/London)

#### Scenario: Filtered autocomplete
- **WHEN** the user types "UTC+8" in the timezone field
- **THEN** the bot SHALL filter suggestions to show matching entries (e.g., `UTC+8`, `UTC+8:30`)

#### Scenario: IANA name autocomplete
- **WHEN** the user types "Asia" in the timezone field
- **THEN** the bot SHALL filter suggestions to show matching IANA zones (e.g., Asia/Taipei, Asia/Tokyo, Asia/Shanghai)

## REMOVED Requirements

### Requirement: Server settings commands
**Reason**: All deprecated `/set_*` commands, `/show_settings`, and `/remove_channel` have been consolidated into the unified `/config` command. The deprecated commands were introduced with warnings in the prior `unified-config-command` change; this change completes the removal.
**Migration**: Use `/config` — no params to view, params to update, `reset:True` to delete all settings.

### Requirement: Channel prerequisite
**Reason**: The channel prerequisite logic is now handled within the unified `/config` command's first-time setup check. No separate requirement needed.
**Migration**: `/config time:08:00` on an unconfigured server will prompt for channel parameter.

## PBT Properties

### Property: Mode dispatch determinism
- **INVARIANT**: For any combination of `/config` parameters, exactly one mode (show/reset/update) is selected
- **FALSIFICATION**: Generate all 2^6 combinations of the 6 optional params; assert each maps to exactly one mode or a mutual-exclusion error

### Property: Reset mutual exclusion completeness
- **INVARIANT**: `reset:True` combined with any non-default setting param always produces the mutual-exclusion error
- **FALSIFICATION**: Generate all subsets of `{channel, role, time, timezone, clear_role}` with `reset=True`; assert error for every non-empty subset

### Property: Show-DB consistency
- **INVARIANT**: `/config` no-params always reflects the current DB state (show is a pure projection)
- **FALSIFICATION**: Sequence: update → show; compare show embed fields with DB snapshot after update

### Property: Update idempotency
- **INVARIANT**: Applying the same update twice from identical state produces identical DB state
- **FALSIFICATION**: Apply identical update payload twice; assert DB row identical after first and second call

### Property: All responses ephemeral
- **INVARIANT**: Every response path in `/config` (show/update/reset/error) uses `ephemeral=True`
- **FALSIFICATION**: Enumerate all code paths; assert `ephemeral=True` in every `send_message`/`followup.send` call
