## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: i18n configuration section
The configuration SHALL support an `i18n` section with `default_locale` and `supported_locales` keys.

#### Scenario: Default locale configuration
- **WHEN** `config.toml` contains `[i18n]` with `default_locale = "zh-TW"`
- **THEN** the system SHALL use "zh-TW" as the fallback locale when no guild or interaction locale is available

#### Scenario: Supported locales configuration
- **WHEN** `config.toml` contains `supported_locales = ["zh-TW", "en-US", "zh-CN"]`
- **THEN** the system SHALL only accept those three locales for resolution

#### Scenario: Missing i18n section
- **WHEN** `config.toml` does not contain an `[i18n]` section
- **THEN** the system SHALL default to `default_locale = "zh-TW"` and `supported_locales = ["zh-TW", "en-US", "zh-CN"]`
