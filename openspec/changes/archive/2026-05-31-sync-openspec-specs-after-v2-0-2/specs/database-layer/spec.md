## MODIFIED Requirements

### Requirement: Settings database management
The SettingsDatabaseManager SHALL manage per-server Discord settings with CRUD operations, including notification channel, role, post time, timezone, and language.

#### Scenario: Store server settings
- **WHEN** a server configures channel, role, post_time, timezone, or language
- **THEN** the settings SHALL be persisted in the database

#### Scenario: Retrieve server settings
- **WHEN** settings are requested for a server
- **THEN** the manager SHALL return all configured settings for that server_id, including `language`

#### Scenario: Default language on new server
- **WHEN** a server is configured for the first time without specifying language
- **THEN** the `language` field SHALL default to `zh-TW`

### Requirement: Persisted runtime tables
The runtime SHALL persist data only in the following SQLite tables: `server_settings`, `llm_translate_results`, and `llm_inspire_results`. The `server_settings` table SHALL include a `language` column, and LLM cache tables SHALL include `locale` in their primary keys.

#### Scenario: Runtime schema initialization
- **WHEN** the runtime initializes its database managers
- **THEN** it SHALL create or reuse `server_settings` with `language`, `llm_translate_results` with locale-aware primary key, and `llm_inspire_results` with locale-aware primary key

#### Scenario: Existing server settings migration
- **WHEN** the bot starts with an existing database that lacks `server_settings.language`
- **THEN** the system SHALL add the column with default value `zh-TW`

#### Scenario: Existing LLM cache migration
- **WHEN** the bot starts with existing LLM cache tables that lack `locale`
- **THEN** the system SHALL recreate those cache tables because cached LLM responses are derived data

### Requirement: LLM cache database management
The LLMTranslateDatabaseManager and LLMInspireDatabaseManager SHALL cache LLM responses with composite primary key `(source, problem_id, locale)`.

#### Scenario: Cache with TTL
- **WHEN** a cached LLM response is retrieved
- **THEN** the manager SHALL check the timestamp against the configured TTL

#### Scenario: Expired cache
- **WHEN** a cached response exceeds the TTL
- **THEN** the manager SHALL treat it as a cache miss

#### Scenario: Translation cache locale isolation
- **WHEN** a translation is cached for a problem in `zh-TW`
- **THEN** a later request for the same problem in `en-US` SHALL NOT return the zh-TW cached result

#### Scenario: Inspiration cache locale isolation
- **WHEN** inspiration is cached for a problem in `en-US`
- **THEN** a later request for the same problem in `zh-CN` SHALL NOT return the en-US cached result
