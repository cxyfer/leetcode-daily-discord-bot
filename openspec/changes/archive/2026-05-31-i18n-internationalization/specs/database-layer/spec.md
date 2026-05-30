## MODIFIED Requirements

### Requirement: Settings database management
The SettingsDatabaseManager SHALL manage per-server Discord settings with CRUD operations, including a `language` field.

#### Scenario: Store server settings
- **WHEN** a server configures channel, role, post_time, timezone, or language
- **THEN** the settings SHALL be persisted in the database

#### Scenario: Retrieve server settings
- **WHEN** settings are requested for a server
- **THEN** the manager SHALL return all configured settings for that server_id, including `language`

#### Scenario: Default language on new server
- **WHEN** a server is configured for the first time without specifying language
- **THEN** the `language` field SHALL default to "zh-TW"

### Requirement: Persisted runtime tables
The runtime SHALL persist data only in the following SQLite tables: `server_settings`, `llm_translate_results`, and `llm_inspire_results`. The `server_settings` table SHALL include a `language` column. The LLM cache tables SHALL include a `locale` column in their primary keys.

#### Scenario: Runtime schema initialization
- **WHEN** the runtime initializes its database managers
- **THEN** it SHALL create or reuse `server_settings` (with `language` column), `llm_translate_results` (with `locale` in PK), and `llm_inspire_results` (with `locale` in PK)

#### Scenario: Schema migration for existing databases
- **WHEN** the bot starts with an existing database that lacks the `language` column in `server_settings`
- **THEN** the system SHALL execute `ALTER TABLE server_settings ADD COLUMN language TEXT NOT NULL DEFAULT 'zh-TW'`

#### Scenario: LLM cache table migration
- **WHEN** the bot starts with existing LLM cache tables that lack the `locale` column
- **THEN** the system SHALL drop and recreate those tables (cache is ephemeral with 7-day TTL)

## ADDED Requirements

### Requirement: Locale-aware LLM cache isolation
LLM cache tables SHALL include `locale` in their primary key to prevent cross-language cache pollution.

#### Scenario: Translation cache per locale
- **WHEN** a translation is cached for problem "two-sum" in "zh-TW"
- **THEN** a subsequent request for "two-sum" in "en-US" SHALL NOT return the zh-TW cached result

#### Scenario: Inspiration cache per locale
- **WHEN** an inspiration is cached for problem "two-sum" in "en-US"
- **THEN** a subsequent request for "two-sum" in "zh-CN" SHALL NOT return the en-US cached result
