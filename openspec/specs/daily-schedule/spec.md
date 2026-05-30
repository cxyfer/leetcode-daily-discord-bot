# daily-schedule Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Per-server daily challenge scheduling
The system SHALL maintain independent daily challenge schedules for each Discord server using APScheduler with CronTrigger, and scheduled output SHALL use the guild's resolved language.

#### Scenario: Schedule initialization on startup
- **WHEN** the bot starts and `initialize_schedules()` is called
- **THEN** the system SHALL load all server settings from the database and create a CronTrigger job for each server with a configured channel

#### Scenario: Timezone-aware scheduling
- **WHEN** a server has a configured timezone
- **THEN** the CronTrigger SHALL use the parsed timezone for job execution timing

#### Scenario: Invalid timezone in database
- **WHEN** a server has an unparseable timezone string in the database
- **THEN** the system SHALL log the error and skip scheduling for that server without crashing

### Requirement: Schedule management
The system SHALL support adding, rescheduling, and removing server schedules at runtime.

#### Scenario: Add new schedule
- **WHEN** a server configures a channel and post time
- **THEN** a new APScheduler job SHALL be created with the specified time and timezone

#### Scenario: Reschedule existing job
- **WHEN** a server changes its post time or timezone
- **THEN** the existing job SHALL be removed and a new job created with updated settings

#### Scenario: Remove schedule
- **WHEN** a server removes its notification channel
- **THEN** the corresponding APScheduler job SHALL be removed

#### Scenario: Invalid time or timezone
- **WHEN** a server has an invalid post_time format or timezone
- **THEN** the error SHALL be logged but SHALL NOT crash the bot

### Requirement: Daily challenge delivery
The system SHALL fetch and post the daily challenge to the configured channel at the scheduled time using localized UI text.

#### Scenario: Successful localized delivery
- **WHEN** a scheduled job fires for a server with `language = "en-US"`
- **THEN** the system SHALL fetch the current daily challenge and post embed text, field names, button labels, and footer text in English

#### Scenario: Delivery without language setting
- **WHEN** a scheduled job fires for a server without a language setting
- **THEN** the system SHALL resolve locale from configured default and hard fallback rules before posting

### Requirement: Job configuration defaults
APScheduler jobs SHALL use specific defaults for reliability.

#### Scenario: Misfire grace time
- **WHEN** a job misses its scheduled time (e.g., bot was offline)
- **THEN** the job SHALL still execute if within the 5-minute misfire grace period

#### Scenario: Max instances
- **WHEN** a job is triggered while a previous instance is still running
- **THEN** the scheduler SHALL allow up to 3 concurrent instances

### Requirement: Job persistence across restarts
APScheduler jobs use MemoryJobStore and SHALL be recreated from database settings on each bot restart.

#### Scenario: Bot restart
- **WHEN** the bot restarts
- **THEN** all schedules SHALL be recreated from the database, not from in-memory state

### Requirement: Graceful scheduler shutdown
The scheduler SHALL support graceful shutdown to prevent orphaned jobs.

#### Scenario: Bot shutdown
- **WHEN** the bot process is shutting down
- **THEN** the scheduler SHALL be shut down gracefully, waiting for running jobs to complete

### Requirement: Localized scheduled posts
Scheduled daily challenge posts SHALL use the guild's resolved language for all UI text, without requiring an interaction context.

#### Scenario: Daily post uses guild language
- **WHEN** a scheduled daily post fires for a server with `language = "en-US"`
- **THEN** all embed text, field names, button labels, and footer text SHALL be in English

#### Scenario: Daily post with no language setting
- **WHEN** a scheduled daily post fires for a server without a language setting
- **THEN** the system SHALL resolve locale from the guild database setting → config default → "zh-TW"

#### Scenario: Locale resolution without interaction
- **WHEN** a scheduled post needs locale resolution
- **THEN** it SHALL use keyword arguments when calling `resolve_locale`, skipping interaction-level fallbacks

#### Scenario: Post role mention unchanged by locale
- **WHEN** a scheduled localized daily post includes a configured role mention
- **THEN** localization SHALL NOT alter the role mention behavior
