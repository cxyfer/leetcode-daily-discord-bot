## MODIFIED Requirements

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

### Requirement: Daily challenge delivery
The system SHALL fetch and post the daily challenge to the configured channel at the scheduled time using localized UI text.

#### Scenario: Successful localized delivery
- **WHEN** a scheduled job fires for a server with `language = "en-US"`
- **THEN** the system SHALL fetch the current daily challenge and post embed text, field names, button labels, and footer text in English

#### Scenario: Delivery without language setting
- **WHEN** a scheduled job fires for a server without a language setting
- **THEN** the system SHALL resolve locale from configured default and hard fallback rules before posting

### Requirement: Localized scheduled posts
Scheduled daily challenge posts SHALL resolve locale without requiring an interaction context.

#### Scenario: Locale resolution without interaction
- **WHEN** a scheduled post needs locale resolution
- **THEN** it SHALL use guild settings and configuration fallback while skipping interaction-level locale fallbacks

#### Scenario: Post role mention unchanged by locale
- **WHEN** a scheduled localized daily post includes a configured role mention
- **THEN** localization SHALL NOT alter the role mention behavior
