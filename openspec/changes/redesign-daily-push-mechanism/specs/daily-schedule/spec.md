## MODIFIED Requirements

### Requirement: Per-server daily challenge scheduling
The system SHALL maintain one independent APScheduler job for each configured `(server_id, source)` daily push. Supported sources SHALL be `leetcode.com`, `sheep`, and `0x3f`, and scheduled output SHALL use the guild's resolved language.

#### Scenario: Schedule initialization on startup
- **WHEN** the bot starts and `initialize_schedules()` is called
- **THEN** the system SHALL load every daily push joined with guild language and create one CronTrigger job per valid row

#### Scenario: Three source schedules
- **WHEN** one server has configured all three supported sources
- **THEN** the scheduler SHALL own three independent jobs for that server

#### Scenario: Timezone-aware scheduling
- **WHEN** a push has a configured timezone
- **THEN** its CronTrigger SHALL use that parsed timezone independently of other pushes

#### Scenario: Invalid timezone in one push
- **WHEN** one source push has an unparseable timezone
- **THEN** the system SHALL log and skip only that source without crashing or suppressing the server's other jobs

### Requirement: Schedule management
The system SHALL support adding, rescheduling, and removing jobs by server and source at runtime.

#### Scenario: Add new source schedule
- **WHEN** a server configures a new source push with channel and post time
- **THEN** a job SHALL be created for only that server/source pair

#### Scenario: Reschedule one source
- **WHEN** a server changes one source's post time or timezone
- **THEN** only that source's existing job SHALL be replaced

#### Scenario: Remove one source schedule
- **WHEN** a server removes one source push
- **THEN** only the corresponding server/source job SHALL be removed

#### Scenario: Reset server schedules
- **WHEN** a server resets all settings
- **THEN** every scheduler job owned by that server SHALL be removed

#### Scenario: Invalid time or timezone
- **WHEN** one stored push has an invalid post time or timezone
- **THEN** the error SHALL be logged without crashing the bot or removing valid peer jobs

### Requirement: Daily challenge delivery
The system SHALL fetch and post the configured daily source to the selected channel at the scheduled time using localized UI text. It SHALL prevent concurrent duplicate delivery for the same server, channel, source, and daily date within one bot process.

#### Scenario: Successful source delivery
- **WHEN** a scheduled Sheep or 0x3f job fires
- **THEN** the system SHALL fetch the current payload using that canonical source and post it to that push's channel

#### Scenario: Independent role mention
- **WHEN** one source push has a configured role
- **THEN** only that source's scheduled message SHALL mention that role

#### Scenario: Successful localized delivery
- **WHEN** a scheduled job fires for a server with `language = "en-US"`
- **THEN** the source's embed text, field names, button labels, and footer text SHALL be rendered in English

#### Scenario: Delivery without language setting
- **WHEN** a scheduled job fires for a server without an explicit language setting
- **THEN** the system SHALL resolve locale from configured default and hard fallback rules before posting

#### Scenario: Concurrent duplicate source delivery
- **WHEN** two scheduled attempts for the same server, channel, source, and daily date overlap
- **THEN** only one attempt SHALL send a Discord message

#### Scenario: Different sources do not collide
- **WHEN** two different sources run for the same server, channel, and date
- **THEN** each source SHALL remain eligible to send its own message

#### Scenario: Unavailable source date
- **WHEN** the upstream daily endpoint returns HTTP 404 for a source's current publishing date
- **THEN** the scheduled job SHALL log an expected no-delivery result and SHALL NOT post a Discord message

#### Scenario: Multi-problem source payload
- **WHEN** a scheduled payload contains more than one problem
- **THEN** the message SHALL use the existing problems overview embed and problem-detail buttons in source order

#### Scenario: Single-problem source payload
- **WHEN** a scheduled payload contains exactly one problem
- **THEN** the message SHALL preserve the existing daily problem presentation

### Requirement: Job configuration defaults
APScheduler jobs SHALL use specific defaults for reliability and SHALL NOT run overlapping instances of the same server/source job.

#### Scenario: Misfire grace time
- **WHEN** a job misses its scheduled time
- **THEN** it SHALL still execute if within the 5-minute misfire grace period

#### Scenario: Max instances
- **WHEN** one server/source job is triggered while its previous instance is still running
- **THEN** the scheduler SHALL prevent a concurrent second instance of that job

#### Scenario: Peer source concurrency
- **WHEN** another source job for the same server is ready to run
- **THEN** the first source's max-instance limit SHALL NOT suppress the peer job

#### Scenario: Coalesced missed runs
- **WHEN** multiple missed executions for one server/source job are eligible after recovery
- **THEN** the scheduler SHALL coalesce them into a single execution

### Requirement: Job persistence across restarts
APScheduler jobs use MemoryJobStore and SHALL be recreated from normalized daily push settings on each bot restart.

#### Scenario: Bot restart
- **WHEN** the bot restarts
- **THEN** every valid persisted server/source push SHALL be recreated as an in-memory scheduler job

