## ADDED Requirements

### Requirement: Settings database management
The SettingsDatabaseManager SHALL manage per-server Discord settings with CRUD operations.

#### Scenario: Store server settings
- **WHEN** a server configures channel, role, post_time, or timezone
- **THEN** the settings SHALL be persisted in the database

#### Scenario: Retrieve server settings
- **WHEN** settings are requested for a server
- **THEN** the manager SHALL return all configured settings for that server_id

### Requirement: Problems database management
The ProblemsDatabaseManager SHALL store and retrieve problem data with composite primary key (source, id).

#### Scenario: Upsert problem data
- **WHEN** problem data is saved
- **THEN** the manager SHALL use INSERT OR REPLACE to handle both new and updated problems

#### Scenario: Problem ID validation
- **WHEN** a problem without an ID is saved
- **THEN** the manager SHALL raise a ValueError

#### Scenario: JSON field serialization
- **WHEN** complex fields (tags, similar_questions) are stored
- **THEN** the manager SHALL serialize them as JSON strings

### Requirement: Daily challenge database management
The DailyChallengeDatabaseManager SHALL track daily challenges with composite primary key (date, domain).

#### Scenario: Store daily challenge
- **WHEN** a daily challenge is fetched
- **THEN** the manager SHALL store it with the date and domain as the composite key

#### Scenario: One challenge per day per domain
- **WHEN** a duplicate (date, domain) entry is inserted
- **THEN** the manager SHALL replace the existing entry

### Requirement: Embedding database management
The EmbeddingDatabaseManager SHALL manage embedding metadata with composite primary key (source, problem_id).

#### Scenario: Track embedding metadata
- **WHEN** an embedding is generated
- **THEN** the manager SHALL store metadata (model, dimensions, timestamp) separately from the vector data

### Requirement: LLM cache database management
The LLMTranslateDatabaseManager and LLMInspireDatabaseManager SHALL cache LLM responses with composite primary key (problem_id, domain).

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
