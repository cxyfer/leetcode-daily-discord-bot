# i18n-service Specification

## Purpose
TBD - created by applying change sync-openspec-specs-after-v2-0-2. Update Purpose after archive.
## Requirements
### Requirement: Locale resolution with priority fallback
The I18nService SHALL resolve the active locale using persisted guild settings, Discord locale hints, configured defaults, and a hard fallback.

#### Scenario: Guild has explicit language setting
- **WHEN** a guild has a `language` value in `server_settings`
- **THEN** the service SHALL return that value as the resolved locale

#### Scenario: Guild locale fallback
- **WHEN** a guild has no persisted language and `interaction.guild_locale` is available
- **THEN** the service SHALL return `interaction.guild_locale` as the resolved locale

#### Scenario: Interaction locale fallback
- **WHEN** no guild setting or guild locale is available and `interaction.locale` is available
- **THEN** the service SHALL return `interaction.locale` as the resolved locale

#### Scenario: Scheduled post without interaction
- **WHEN** a scheduled daily post has no interaction context
- **THEN** the service SHALL resolve locale from guild database setting, then config default, then `zh-TW`

#### Scenario: All signals missing
- **WHEN** no guild setting, Discord locale, interaction locale, or config default is available
- **THEN** the service SHALL return `zh-TW`

### Requirement: Translation key lookup
The I18nService SHALL provide translation lookup with parameter interpolation and fallback behavior.

#### Scenario: Simple key lookup
- **WHEN** `t("errors.api.processing", "en-US")` is called
- **THEN** the service SHALL return the corresponding English string from the en-US locale file

#### Scenario: Parameter interpolation
- **WHEN** `t("errors.validation.not_found_for_date", "zh-TW", date="2025-07-01")` is called and the template contains `{date}`
- **THEN** the service SHALL return the string with `{date}` replaced by `2025-07-01`

#### Scenario: Missing key in target locale
- **WHEN** a key does not exist in the target locale file
- **THEN** the service SHALL fall back to the zh-TW value and log a warning

#### Scenario: Missing key in all locales
- **WHEN** a key does not exist in any locale file
- **THEN** the service SHALL return the raw key name and log an error

### Requirement: Locale file loading
The I18nService SHALL load JSON locale files from `src/bot/i18n/locales/` at initialization.

#### Scenario: Load supported locale files
- **WHEN** the service initializes
- **THEN** it SHALL load `zh-TW.json`, `en-US.json`, and `zh-CN.json` into memory

#### Scenario: Missing locale file
- **WHEN** a locale file does not exist on disk
- **THEN** the service SHALL log a warning and continue with available locales

#### Scenario: Invalid locale JSON
- **WHEN** a locale file contains invalid JSON
- **THEN** the service SHALL log an error and skip that locale

### Requirement: Supported locale validation
The I18nService SHALL validate resolved locales against the configured supported locale list.

#### Scenario: Unsupported locale requested
- **WHEN** a locale not in `supported_locales` is requested
- **THEN** the service SHALL fall back to the configured default locale

#### Scenario: Config defines supported locales
- **WHEN** `config.toml` contains `i18n.supported_locales = ["zh-TW", "en-US", "zh-CN"]`
- **THEN** only those three locales SHALL be accepted
