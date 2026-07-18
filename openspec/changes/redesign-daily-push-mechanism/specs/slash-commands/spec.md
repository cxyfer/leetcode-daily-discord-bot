## MODIFIED Requirements

### Requirement: Unified config command
The `/config` command SHALL allow server administrators to view and update guild language plus source-specific daily pushes. Push fields SHALL include source, channel, role, post time, and timezone. Source choices SHALL resolve to `leetcode.com`, `sheep`, or `0x3f`.

#### Scenario: View all settings
- **WHEN** an administrator runs `/config` without parameters
- **THEN** the bot SHALL display guild language and every configured source push

#### Scenario: Legacy source-less update
- **WHEN** an administrator updates channel, role, time, or timezone without specifying source
- **THEN** the command SHALL update the `leetcode.com` push

#### Scenario: Create source push
- **WHEN** an administrator runs `/config source:sheep channel:#daily time:08:00 timezone:UTC+8`
- **THEN** the bot SHALL create or replace only the Sheep push and reschedule only Sheep

#### Scenario: New source requires channel
- **WHEN** an administrator attempts to configure a source that has no existing push without providing channel
- **THEN** the command SHALL reject the request with a localized error

#### Scenario: Partial source update
- **WHEN** an administrator changes the time of an existing 0x3f push
- **THEN** its channel, role, timezone, and the other source pushes SHALL remain unchanged

#### Scenario: Set guild language
- **WHEN** an administrator runs `/config language:en-US`
- **THEN** the bot SHALL update the guild-wide language without selecting or mutating a source push

#### Scenario: Language choice list
- **WHEN** a user types `/config language:`
- **THEN** Discord SHALL display a choice list with `zh-TW`, `en-US`, and `zh-CN`

#### Scenario: Permission check
- **WHEN** a user without `manage_guild` permission runs `/config`
- **THEN** the bot SHALL respond with a localized permission error

## ADDED Requirements

### Requirement: Source-specific push removal
The `/config` command SHALL support removing one source push without changing guild language or other source pushes.

#### Scenario: Remove one source
- **WHEN** an administrator confirms `/config source:sheep remove:true`
- **THEN** the Sheep push and its scheduler job SHALL be removed
- **AND** all other guild and push settings SHALL remain unchanged

#### Scenario: Remove requires source
- **WHEN** an administrator uses `remove:true` without an explicit source
- **THEN** the command SHALL reject the request rather than defaulting destructive behavior to LeetCode

#### Scenario: Remove conflict
- **WHEN** `remove:true` is combined with any setting update or `reset:true`
- **THEN** the command SHALL reject the conflicting request

### Requirement: Whole-guild configuration reset
The `/config reset:true` operation SHALL retain its whole-guild meaning and SHALL remove guild settings plus every source push only after confirmation.

#### Scenario: Confirm whole-guild reset
- **WHEN** an administrator confirms a reset
- **THEN** guild language, all source pushes, and every scheduler job for that server SHALL be removed

#### Scenario: Reset conflict
- **WHEN** `reset:true` is combined with a source, removal, or setting update
- **THEN** the command SHALL reject the conflicting request

### Requirement: Source configuration display
Configuration responses SHALL distinguish guild-wide language from each source's independent push fields.

#### Scenario: Display three pushes
- **WHEN** a server has configured all supported sources
- **THEN** `/config` SHALL show one language value and separate LeetCode, Sheep, and 0x3f sections with channel, role, time, and timezone

#### Scenario: Confirmation interaction identity
- **WHEN** a source removal or whole-guild reset confirmation is created
- **THEN** its custom ID SHALL identify the action, guild, source when applicable, requesting user, and expiry within Discord's 100-character limit

