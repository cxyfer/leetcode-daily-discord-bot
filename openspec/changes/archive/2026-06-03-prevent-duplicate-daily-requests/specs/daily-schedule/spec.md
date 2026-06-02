## MODIFIED Requirements

### Requirement: Daily challenge delivery
The system SHALL fetch and post the daily challenge to the configured channel at the scheduled time using localized UI text, while preventing concurrent duplicate delivery for the same server, channel, domain, and daily date within one bot process.

#### Scenario: Successful localized delivery
- **WHEN** a scheduled job fires for a server with `language = "en-US"`
- **THEN** the system SHALL fetch the current daily challenge and post embed text, field names, button labels, and footer text in English

#### Scenario: Delivery without language setting
- **WHEN** a scheduled job fires for a server without a language setting
- **THEN** the system SHALL resolve locale from configured default and hard fallback rules before posting

#### Scenario: Concurrent duplicate scheduled delivery
- **WHEN** two scheduled delivery attempts for the same server, channel, domain, and daily date overlap
- **THEN** only one attempt SHALL send a Discord message and the duplicate attempt SHALL be skipped

### Requirement: Job configuration defaults
APScheduler jobs SHALL use specific defaults for reliability and SHALL NOT run overlapping instances of the same server's daily challenge job.

#### Scenario: Misfire grace time
- **WHEN** a job misses its scheduled time (e.g., bot was offline)
- **THEN** the job SHALL still execute if within the 5-minute misfire grace period

#### Scenario: Max instances
- **WHEN** a job is triggered while a previous instance for the same server is still running
- **THEN** the scheduler SHALL prevent a concurrent second instance for that server's daily job

#### Scenario: Coalesced missed runs
- **WHEN** multiple missed executions for the same daily job are eligible to run after scheduler recovery
- **THEN** the scheduler SHALL coalesce them into a single execution
