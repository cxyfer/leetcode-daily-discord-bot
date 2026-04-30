## ADDED Requirements

### Requirement: Locale resolution with 5-level priority
The I18nService SHALL resolve the active locale using a 5-level priority chain.

#### Scenario: Guild has explicit language setting
- **WHEN** a guild has a `language` value in `server_settings`
- **THEN** the service SHALL return that value as the resolved locale

#### Scenario: Guild has no language setting but Discord has preferred locale
- **WHEN** a guild has no `language` in `server_settings` and `interaction.guild_locale` is not None
- **THEN** the service SHALL return `interaction.guild_locale` as the resolved locale

#### Scenario: User interaction without guild context
- **WHEN** there is no guild context (DM) and `interaction.locale` is not None
- **THEN** the service SHALL return `interaction.locale` as the resolved locale

#### Scenario: Scheduled post with no interaction
- **WHEN** a scheduled daily post has no interaction context
- **THEN** the service SHALL resolve locale from guild DB setting → config default → "zh-TW"

#### Scenario: All signals missing
- **WHEN** no guild setting, no guild_locale, no interaction locale, and no config default exist
- **THEN** the service SHALL return "zh-TW" as the hard fallback

### Requirement: Translation key lookup
The I18nService SHALL provide a `t(key, locale, **params)` function that returns translated strings with optional parameter interpolation.

#### Scenario: Simple key lookup
- **WHEN** `t("errors.api.processing", "en-US")` is called
- **THEN** the service SHALL return the corresponding English string from the en-US locale file

#### Scenario: Parameterized string
- **WHEN** `t("commands.daily.not_found", "zh-TW", date="2025-07-01")` is called and the template contains `{date}`
- **THEN** the service SHALL return the string with `{date}` replaced by "2025-07-01"

#### Scenario: Missing key in target locale
- **WHEN** a key does not exist in the target locale file
- **THEN** the service SHALL fall back to zh-TW and log a warning

#### Scenario: Missing key in all locales
- **WHEN** a key does not exist in any locale file
- **THEN** the service SHALL return the raw key name and log an error

### Requirement: Locale file loading
The I18nService SHALL load JSON locale files from `src/bot/i18n/locales/` at initialization.

#### Scenario: Load all supported locales
- **WHEN** the service initializes
- **THEN** it SHALL load `zh-TW.json`, `en-US.json`, and `zh-CN.json` into memory

#### Scenario: Missing locale file
- **WHEN** a locale file does not exist on disk
- **THEN** the service SHALL log an error and continue with available locales

#### Scenario: Invalid JSON in locale file
- **WHEN** a locale file contains invalid JSON
- **THEN** the service SHALL log an error and skip that locale

### Requirement: Supported locale validation
The I18nService SHALL validate that configured locales are in the `supported_locales` list.

#### Scenario: Unsupported locale requested
- **WHEN** a locale not in `supported_locales` is resolved
- **THEN** the service SHALL fall back to the default locale

#### Scenario: Config defines supported locales
- **WHEN** `config.toml` contains `i18n.supported_locales = ["zh-TW", "en-US", "zh-CN"]`
- **THEN** only those three locales SHALL be accepted
