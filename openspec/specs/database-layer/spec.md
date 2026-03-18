# database-layer Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Settings database management
The SettingsDatabaseManager SHALL manage per-server Discord settings with CRUD operations.

#### Scenario: Store server settings
- **WHEN** a server configures channel, role, post_time, or timezone
- **THEN** the settings SHALL be persisted in the database

#### Scenario: Retrieve server settings
- **WHEN** settings are requested for a server
- **THEN** the manager SHALL return all configured settings for that server_id

### Requirement: Persisted runtime tables
The runtime SHALL persist data only in the following SQLite tables: `server_settings`, `llm_translate_results`, and `llm_inspire_results`.

#### Scenario: Runtime schema initialization
- **WHEN** the runtime initializes its database managers
- **THEN** it SHALL create or reuse only `server_settings`, `llm_translate_results`, and `llm_inspire_results` as persisted runtime tables

### Requirement: No local similarity index persistence
The database layer SHALL NOT require local embedding metadata tables, vector storage managers, or other local similarity persistence for `/similar`.

#### Scenario: Similarity request execution
- **WHEN** the `/similar` feature is used
- **THEN** the runtime SHALL delegate similarity search to the remote API instead of persisting local embedding metadata or vectors in SQLite

### Requirement: LLM cache database management
The LLMTranslateDatabaseManager and LLMInspireDatabaseManager SHALL cache LLM responses with composite primary key `(source, problem_id)`.

#### Scenario: Cache with TTL
- **WHEN** a cached LLM response is retrieved
- **THEN** the manager SHALL check the timestamp against the configured TTL (default 10 days)

#### Scenario: Expired cache
- **WHEN** a cached response exceeds the TTL
- **THEN** the manager SHALL treat it as a cache miss

### Requirement: Thread-safe database operations
All database managers SHALL use parameterized queries and support async operations via `asyncio.to_thread`.

#### Scenario: Concurrent access
- **WHEN** multiple cogs access the database concurrently
- **THEN** operations SHALL be thread-safe with proper connection handling

### Requirement: SQL injection prevention
All database operations SHALL use parameterized queries exclusively.

#### Scenario: User-provided input
- **WHEN** user input is used in a database query
- **THEN** the input SHALL be passed as a parameter, never interpolated into the SQL string

