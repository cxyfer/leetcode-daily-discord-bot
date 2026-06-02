## ADDED Requirements

### Requirement: In-flight daily payload reuse
The system SHALL reuse in-flight or short-lived cached daily challenge payload data for identical domain/date requests within one bot process.

#### Scenario: Concurrent current daily payload requests
- **WHEN** multiple daily challenge flows request the current daily payload for the same domain while the first request is still processing
- **THEN** the system SHALL await the same in-flight payload work instead of starting duplicate upstream daily and history fetches

#### Scenario: Short burst after payload completion
- **WHEN** a daily challenge flow requests the same domain/date shortly after a successful payload fetch
- **THEN** the system SHALL reuse the cached payload without calling the upstream daily and history APIs again

#### Scenario: Locale-specific rendering remains independent
- **WHEN** two guilds render the same cached daily payload using different resolved locales
- **THEN** the system SHALL build separate localized Discord embeds and views from the shared payload

### Requirement: Scheduled daily duplicate delivery guard
The system SHALL prevent concurrent duplicate scheduled daily delivery for the same server, channel, domain, and daily date within one bot process.

#### Scenario: Duplicate scheduled delivery already in progress
- **WHEN** a scheduled daily job starts while another scheduled delivery with the same server, channel, domain, and daily date is still running
- **THEN** the system SHALL skip the duplicate delivery attempt and log that the scheduled delivery is already in progress

#### Scenario: Guard cleanup after completion
- **WHEN** a scheduled daily delivery succeeds, fails, or is skipped due to an API error
- **THEN** the system SHALL remove its in-flight delivery key so later legitimate scheduled attempts are not permanently blocked

#### Scenario: Manual daily requests are not persistently suppressed
- **WHEN** a user runs `/daily` after a previous `/daily` request has completed
- **THEN** the bot SHALL still send a valid response while reusing cached payload data when available
