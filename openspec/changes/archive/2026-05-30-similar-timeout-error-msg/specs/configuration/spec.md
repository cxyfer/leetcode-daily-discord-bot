# configuration Delta Specification

## MODIFIED Requirements

### Requirement: Model-specific configuration
The system SHALL support separate configuration for Gemini models and the `/similar` feature. `get_llm_model_config()` SHALL return per-model Gemini settings, and `get_similar_config()` SHALL return a `SimilarConfig` dataclass for remote similarity-search options including a configurable request timeout in seconds.

#### Scenario: Similar config retrieval with timeout
- **WHEN** similar configuration is requested via `get_similar_config()`
- **THEN** the system SHALL return a `SimilarConfig` instance with `top_k`, `min_similarity`, and `timeout` fields, where `timeout` defaults to 300 seconds

#### Scenario: Config.toml similar timeout
- **WHEN** `config.toml` contains `[similar]` with `timeout = 600`
- **THEN** `get_similar_config().timeout` SHALL return 600

#### Scenario: EnvConfig similar defaults
- **WHEN** `config.toml` does not exist and `EnvConfig` is used
- **THEN** `get_similar_config().timeout` SHALL return the `SimilarConfig` dataclass default of 300
