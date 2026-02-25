# configuration Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: TOML-based configuration
The system SHALL load configuration from `config.toml` as the primary source. When `config.toml` does not exist, the system SHALL fall back to `.env` file with a DummyConfig compatibility wrapper.

#### Scenario: TOML loading
- **WHEN** the bot starts and `config.toml` exists
- **THEN** the system SHALL load configuration from `config.toml` in the project root

#### Scenario: Environment variable override
- **WHEN** an environment variable is set (e.g., `DISCORD_TOKEN`)
- **THEN** it SHALL take precedence over the corresponding TOML value

#### Scenario: .env fallback
- **WHEN** `config.toml` does not exist but a `.env` file is present
- **THEN** the system SHALL load `.env` and use a DummyConfig compatibility wrapper for backward compatibility

### Requirement: Nested configuration access
The ConfigManager SHALL support dot-notation access for nested configuration values.

#### Scenario: Dot notation access
- **WHEN** a config value is accessed via `config.get("llm.gemini.api_key")`
- **THEN** the system SHALL traverse the nested TOML structure and return the value

### Requirement: Model-specific configuration
The system SHALL support separate configuration for each LLM and embedding model via dataclasses (EmbeddingModelConfig, RewriteModelConfig, SimilarConfig).

#### Scenario: Model config retrieval
- **WHEN** model configuration is requested
- **THEN** the system SHALL return a dataclass with model-specific settings (model name, API key, base URL, dimensions, etc.)

### Requirement: Cache expiration configuration
The ConfigManager SHALL provide cache expiration settings for different data types.

#### Scenario: Cache TTL retrieval
- **WHEN** cache expiration is requested for a data type (e.g., translation, inspiration)
- **THEN** the system SHALL return the configured TTL in seconds

### Requirement: Lazy singleton pattern
The ConfigManager SHALL use a lazy singleton pattern, initializing only on first access.

#### Scenario: First access
- **WHEN** the config is accessed for the first time
- **THEN** the system SHALL parse the TOML file and cache the result

#### Scenario: Subsequent access
- **WHEN** the config is accessed again
- **THEN** the system SHALL return the cached configuration without re-parsing

### Requirement: Timezone parsing with UTC offset support
The `parse_timezone()` function in `utils/config.py` SHALL accept both IANA timezone names and UTC offset strings, returning a `tzinfo`-compatible object accepted by APScheduler's `CronTrigger`.

#### Scenario: Parse IANA timezone name
- **WHEN** `parse_timezone("Asia/Taipei")` is called
- **THEN** the function SHALL return a `pytz.tzinfo` object equivalent to `pytz.timezone("Asia/Taipei")`

#### Scenario: Parse UTC offset integer hours
- **WHEN** `parse_timezone("UTC+8")` is called
- **THEN** the function SHALL return a `datetime.timezone` with utcoffset of +08:00

#### Scenario: Parse UTC offset with minutes
- **WHEN** `parse_timezone("UTC+5:30")` is called
- **THEN** the function SHALL return a `datetime.timezone` with utcoffset of +05:30

#### Scenario: Parse UTC zero variants
- **WHEN** `parse_timezone("UTC+0")` or `parse_timezone("UTC-0")` is called
- **THEN** the function SHALL return a `datetime.timezone` with utcoffset of +00:00, scheduling-equivalent to `parse_timezone("UTC")`

#### Scenario: Reject out-of-range offset
- **WHEN** `parse_timezone("UTC+15")` or `parse_timezone("UTC-13")` is called
- **THEN** the function SHALL raise `ValueError` with a descriptive message

#### Scenario: Reject malformed input
- **WHEN** `parse_timezone("InvalidZone")` or `parse_timezone("UTC+abc")` is called
- **THEN** the function SHALL raise `ValueError` with supported format examples

#### Scenario: CronTrigger compatibility
- **WHEN** the return value of `parse_timezone()` is passed to `CronTrigger(timezone=...)`
- **THEN** APScheduler SHALL accept it without `TypeError` for both IANA and UTC offset inputs

### Requirement: Shared default constants
`utils/config.py` SHALL export module-level constants `DEFAULT_POST_TIME = "00:00"` and `DEFAULT_TIMEZONE = "UTC"` as the single source of truth for default scheduling values.

#### Scenario: Import from slash commands cog
- **WHEN** `slash_commands_cog.py` needs the default post time or timezone
- **THEN** it SHALL import `DEFAULT_POST_TIME` / `DEFAULT_TIMEZONE` from `utils.config`

#### Scenario: Import from schedule manager cog
- **WHEN** `schedule_manager_cog.py` needs the default post time or timezone
- **THEN** it SHALL import `DEFAULT_POST_TIME` / `DEFAULT_TIMEZONE` from `utils.config`

#### Scenario: Consistency with ConfigManager
- **WHEN** `ConfigManager.post_time` or `ConfigManager.timezone` properties return their defaults
- **THEN** the default values SHALL be identical to `DEFAULT_POST_TIME` and `DEFAULT_TIMEZONE`

