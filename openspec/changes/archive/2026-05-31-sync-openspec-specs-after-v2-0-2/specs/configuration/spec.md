## ADDED Requirements

### Requirement: i18n configuration section
The configuration SHALL support an `i18n` section with default and supported locale settings.

#### Scenario: Default locale configuration
- **WHEN** `config.toml` contains `[i18n]` with `default_locale = "zh-TW"`
- **THEN** the system SHALL use `zh-TW` as the fallback locale when no guild or interaction locale is available

#### Scenario: Supported locales configuration
- **WHEN** `config.toml` contains `supported_locales = ["zh-TW", "en-US", "zh-CN"]`
- **THEN** the system SHALL accept only those locales during locale resolution

#### Scenario: Missing i18n section
- **WHEN** `config.toml` does not contain an `[i18n]` section
- **THEN** the system SHALL default to `default_locale = "zh-TW"` and `supported_locales = ["zh-TW", "en-US", "zh-CN"]`
