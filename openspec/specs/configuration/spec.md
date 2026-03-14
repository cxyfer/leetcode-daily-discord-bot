# configuration Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: TOML-based configuration
The system SHALL load configuration from the repository-root `config.toml` as the primary source. When `config.toml` does not exist, the system SHALL fall back to the repository-root `.env` file with a compatibility wrapper, and both lookup paths SHALL be determined by the shared repository-root path authority.

#### Scenario: TOML loading
- **WHEN** the bot starts and repository-root `config.toml` exists
- **THEN** the system SHALL load configuration from that file regardless of the process current working directory

#### Scenario: Environment variable override
- **WHEN** an environment variable is set (for example `DISCORD_TOKEN`)
- **THEN** it SHALL take precedence over the corresponding TOML value

#### Scenario: .env fallback
- **WHEN** repository-root `config.toml` does not exist but repository-root `.env` is present
- **THEN** the system SHALL load `.env` and use a compatibility wrapper without relying on raw relative paths

### Requirement: Nested configuration access
The ConfigManager SHALL support dot-notation access for nested configuration values.

#### Scenario: Dot notation access
- **WHEN** a config value is accessed via `config.get("llm.gemini.api_key")`
- **THEN** the system SHALL traverse the nested TOML structure and return the value

### Requirement: Model-specific configuration
The system SHALL support separate configuration for Gemini models and the `/similar` feature. `get_llm_model_config()` SHALL return per-model Gemini settings, and `get_similar_config()` SHALL return a `SimilarConfig` dataclass for remote similarity-search options.

#### Scenario: Model config retrieval
- **WHEN** model configuration is requested
- **THEN** the system SHALL return the configured settings for the requested Gemini model or `/similar` runtime options

### Requirement: Cache expiration configuration
The ConfigManager SHALL provide cache expiration settings for different data types.

#### Scenario: Cache TTL retrieval
- **WHEN** cache expiration is requested for a data type (e.g., translation, inspiration)
- **THEN** the system SHALL return the configured TTL in seconds

### Requirement: Lazy singleton pattern
The ConfigManager SHALL use a lazy singleton pattern, initializing only on first access, and path resolution during initialization SHALL be current-working-directory independent.

#### Scenario: First access
- **WHEN** the config is accessed for the first time
- **THEN** the system SHALL resolve the repository root through the shared path authority, parse the repository-root configuration source, and cache the result

#### Scenario: Subsequent access
- **WHEN** the config is accessed again
- **THEN** the system SHALL return the cached configuration without re-parsing or re-evaluating path resolution

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

### Requirement: Repository-root path authority
The configuration and runtime support layers SHALL share a single repository-root path authority for resolving configuration files, environment files, databases, and logs.

#### Scenario: Config file resolution
- **WHEN** the system resolves `config.toml`
- **THEN** it SHALL resolve the file relative to the repository root determined by the shared path authority rather than relative to the current working directory

#### Scenario: Runtime asset resolution
- **WHEN** the system resolves `.env`, `data/`, or `logs/`
- **THEN** it SHALL resolve those paths relative to the repository root determined by the shared path authority rather than relative to the current working directory

