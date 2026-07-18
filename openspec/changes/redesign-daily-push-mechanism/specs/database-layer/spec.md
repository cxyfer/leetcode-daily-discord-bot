## MODIFIED Requirements

### Requirement: Settings database management
The SettingsDatabaseManager SHALL manage guild-wide settings separately from source-specific daily push settings. Guild-wide settings SHALL include language. Each daily push SHALL include server ID, canonical source, notification channel, optional role, post time, and timezone.

#### Scenario: Store guild language
- **WHEN** a server configures its language
- **THEN** the language SHALL be persisted once for that server independently of its push rows

#### Scenario: Store independent source pushes
- **WHEN** a server configures pushes for `leetcode.com`, `sheep`, and `0x3f`
- **THEN** each source's channel, role, post time, and timezone SHALL be persisted independently

#### Scenario: Update one source
- **WHEN** a server updates the post time for its `sheep` push
- **THEN** the `leetcode.com` and `0x3f` push rows SHALL remain unchanged

#### Scenario: Retrieve all server configuration
- **WHEN** settings are requested for a server
- **THEN** the manager SHALL return the guild-wide settings and every configured source push

#### Scenario: Default language on new server
- **WHEN** a server is configured for the first time without specifying language
- **THEN** the guild language SHALL default to `zh-TW`

### Requirement: Persisted runtime tables
The runtime SHALL persist settings in normalized `server_settings` and `daily_push_settings` tables alongside `llm_translate_results` and `llm_inspire_results`. The `server_settings` table SHALL own guild language. The `daily_push_settings` table SHALL own source-specific delivery fields and SHALL use `(server_id, source)` as its primary key. LLM cache tables SHALL include `locale` in their primary keys.

#### Scenario: Runtime schema initialization
- **WHEN** the runtime initializes a new database
- **THEN** it SHALL create normalized guild settings, daily push settings, and locale-aware LLM cache tables

#### Scenario: Supported push sources
- **WHEN** a daily push row is inserted
- **THEN** its source SHALL be one of `leetcode.com`, `sheep`, or `0x3f`

#### Scenario: Maximum pushes per server
- **WHEN** a server configures every supported source
- **THEN** the schema SHALL allow exactly one row per source and therefore at most three rows for that server

#### Scenario: Duplicate source rejected
- **WHEN** a second push row is inserted for the same server and source
- **THEN** the database primary key SHALL reject the duplicate

#### Scenario: Guild reset cascades to pushes
- **WHEN** guild settings are deleted
- **THEN** all daily push rows owned by that server SHALL also be deleted

#### Scenario: Existing LLM cache migration
- **WHEN** the bot starts with existing LLM cache tables that lack `locale`
- **THEN** the system SHALL recreate those cache tables because cached LLM responses are derived data

## ADDED Requirements

### Requirement: Legacy push schema migration
The runtime SHALL migrate the legacy single-push `server_settings` schema to normalized settings without losing existing configuration. It SHALL create a database backup before destructive schema changes and SHALL perform copying, validation, and legacy-table removal in one SQLite transaction.

#### Scenario: Legacy row becomes LeetCode push
- **WHEN** a legacy server row contains channel, role, post time, timezone, and language
- **THEN** language SHALL be copied to normalized `server_settings`
- **AND** the delivery fields SHALL be copied to `daily_push_settings` with source `leetcode.com`

#### Scenario: Migration validation succeeds
- **WHEN** every legacy server ID exists in both the normalized guild row and migrated LeetCode push row and row counts match
- **THEN** the migration SHALL remove the temporary legacy table and commit

#### Scenario: Migration validation fails
- **WHEN** copied row counts or server identities do not match the legacy table
- **THEN** the migration SHALL roll back and leave the legacy database usable

#### Scenario: Migration backup
- **WHEN** a legacy schema is detected before destructive DDL
- **THEN** the runtime SHALL create a timestamped SQLite backup beside the database and SHALL NOT automatically delete it

#### Scenario: Migration is idempotent
- **WHEN** the bot starts with the normalized schema after a successful migration
- **THEN** it SHALL reuse that schema without creating another legacy migration backup or duplicate push rows

#### Scenario: Manual cleanup preserves legacy pushes
- **WHEN** the cleanup utility rebuilds a legacy runtime database
- **THEN** it SHALL preserve every legacy schedule as a normalized `leetcode.com` push

