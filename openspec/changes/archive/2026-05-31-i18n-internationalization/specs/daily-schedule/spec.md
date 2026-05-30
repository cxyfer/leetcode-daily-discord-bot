## MODIFIED Requirements

### Requirement: Per-server daily challenge scheduling
The system SHALL maintain independent daily challenge schedules for each Discord server using APScheduler with CronTrigger, with all UI text in the guild's resolved language.

#### Scenario: Schedule initialization on startup
- **WHEN** the bot starts and `initialize_schedules()` is called
- **THEN** the system SHALL load all server settings from the database and create a CronTrigger job for each server with a configured channel; servers without a configured channel SHALL be skipped

#### Scenario: Timezone-aware scheduling
- **WHEN** a server has a configured timezone (IANA name or UTC offset string)
- **THEN** the CronTrigger SHALL use the `tzinfo` object returned by `parse_timezone()` for job execution timing

#### Scenario: Invalid timezone in database
- **WHEN** a server has an unparseable timezone string in the database
- **THEN** the system SHALL catch the `ValueError` from `parse_timezone()`, log the error, and skip scheduling for that server without crashing the scheduler loop

### Requirement: Schedule management
The system SHALL support adding, rescheduling, and removing server schedules at runtime.

#### Scenario: Add new schedule
- **WHEN** a server configures a channel and post time
- **THEN** a new APScheduler job SHALL be created with the specified time and timezone

#### Scenario: Reschedule existing job
- **WHEN** a server changes its post time or timezone
- **THEN** the existing job SHALL be removed and a new job created with updated settings

## ADDED Requirements

### Requirement: Localized scheduled posts
Scheduled daily challenge posts SHALL use the guild's resolved language for all UI text, without requiring an interaction context.

#### Scenario: Daily post uses guild language
- **WHEN** a scheduled daily post fires for a server with `language = "en-US"`
- **THEN** all embed text, field names, button labels, and footer text SHALL be in English

#### Scenario: Daily post with no language setting
- **WHEN** a scheduled daily post fires for a server without a language setting
- **THEN** the system SHALL resolve locale from guild_locale → config default → "zh-TW"

#### Scenario: Locale resolution without interaction
- **WHEN** a scheduled post needs to resolve locale
- **THEN** it SHALL use `resolve_locale(guild_id, guild_locale=None, interaction_locale=None)` which skips interaction-level fallbacks
