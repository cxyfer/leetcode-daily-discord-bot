## ADDED Requirements

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
