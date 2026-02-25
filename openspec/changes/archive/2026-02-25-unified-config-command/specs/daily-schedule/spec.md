## MODIFIED Requirements

### Requirement: Per-server daily challenge scheduling
The system SHALL maintain independent daily challenge schedules for each Discord server using APScheduler with CronTrigger.

#### Scenario: Schedule initialization on startup
- **WHEN** the bot starts and `initialize_schedules()` is called
- **THEN** the system SHALL load all server settings from the database and create a CronTrigger job for each server with a configured channel; servers without a configured channel SHALL be skipped

#### Scenario: Timezone-aware scheduling
- **WHEN** a server has a configured timezone (IANA name or UTC offset string)
- **THEN** the CronTrigger SHALL use the `tzinfo` object returned by `parse_timezone()` for job execution timing

#### Scenario: Invalid timezone in database
- **WHEN** a server has an unparseable timezone string in the database
- **THEN** the system SHALL catch the `ValueError` from `parse_timezone()`, log the error, and skip scheduling for that server without crashing the scheduler loop
