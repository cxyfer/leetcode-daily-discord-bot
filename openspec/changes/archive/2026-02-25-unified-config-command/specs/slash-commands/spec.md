## ADDED Requirements

### Requirement: Unified config command
The `/config` command SHALL allow server admins to set all server configuration in a single invocation with optional parameters: `channel`, `role`, `time`, `timezone`, and `clear_role`.

#### Scenario: First-time setup with all parameters
- **WHEN** an admin with `manage_guild` permission runs `/config channel:#general time:08:00 timezone:UTC+8`
- **THEN** the bot SHALL save all settings and trigger schedule creation, responding with a summary of all configured values

#### Scenario: Partial update
- **WHEN** an admin runs `/config time:09:00` on a server with existing settings
- **THEN** the bot SHALL update only `post_time` to `09:00`, preserving all other settings, and trigger reschedule

#### Scenario: First-time setup without channel
- **WHEN** an admin runs `/config time:08:00` on a server with no existing settings
- **THEN** the bot SHALL respond with an ephemeral error stating channel is required for first-time setup, with usage example

#### Scenario: No parameters provided
- **WHEN** an admin runs `/config` without any parameters
- **THEN** the bot SHALL respond with an ephemeral error requesting at least one parameter

#### Scenario: Atomic validation failure
- **WHEN** an admin runs `/config time:08:00 timezone:InvalidZone`
- **THEN** the bot SHALL reject the entire request without updating any field, returning the timezone validation error

#### Scenario: Permission check
- **WHEN** a user without `manage_guild` permission runs `/config`
- **THEN** the bot SHALL respond with an ephemeral permission error

#### Scenario: Guild-only enforcement
- **WHEN** a user runs `/config` in a DM
- **THEN** the bot SHALL respond indicating this command cannot be used in DMs

#### Scenario: Success response with full state
- **WHEN** any `/config` update succeeds
- **THEN** the bot SHALL display all current settings (channel mention, role mention or "未設定", post_time, timezone) in an ephemeral message

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

## MODIFIED Requirements

### Requirement: Server settings commands
The bot SHALL provide commands to configure per-server settings.

#### Scenario: Set notification channel (deprecated)
- **WHEN** an admin runs `/set_channel` with a channel
- **THEN** the bot SHALL save the channel, trigger schedule creation/update, and emit a deprecation warning recommending `/config channel:<channel>`

#### Scenario: Set mention role (deprecated)
- **WHEN** an admin runs `/set_role` with a role
- **THEN** the bot SHALL save the role, and emit a deprecation warning recommending `/config role:<role>`

#### Scenario: Set post time (deprecated)
- **WHEN** an admin runs `/set_post_time` with a time (HH:MM)
- **THEN** the bot SHALL save the time, reschedule, and emit a deprecation warning recommending `/config time:<time>`

#### Scenario: Set timezone (deprecated)
- **WHEN** an admin runs `/set_timezone` with a valid timezone
- **THEN** the bot SHALL save the timezone, reschedule, and emit a deprecation warning recommending `/config timezone:<timezone>`

#### Scenario: Show settings
- **WHEN** a user runs `/show_settings`
- **THEN** the bot SHALL display all current server settings; if no settings exist, the empty-state message SHALL reference `/config` instead of `/set_channel`

#### Scenario: Remove channel
- **WHEN** an admin runs `/remove_channel`
- **THEN** the bot SHALL remove the notification channel and cancel the scheduled job (unchanged)

### Requirement: Channel prerequisite
Server settings that depend on a channel (role, post_time, timezone) SHALL require a channel to be set first.

#### Scenario: Setting without channel
- **WHEN** an admin tries to set post_time without a channel configured
- **THEN** the bot SHALL respond with an error indicating a channel must be set first via `/config channel:<channel>`
