## ADDED Requirements

### Requirement: discord.py Translator implementation
The system SHALL implement a `discord.app_commands.Translator` subclass for slash command metadata localization.

#### Scenario: Translator registration at startup
- **WHEN** the bot starts
- **THEN** it SHALL call `await bot.tree.set_translator(translator)` BEFORE `await bot.tree.sync()`

#### Scenario: Translation for command descriptions
- **WHEN** `tree.sync()` is called
- **THEN** the Translator SHALL provide translations for all command descriptions in zh-TW, en-US, and zh-CN

#### Scenario: Translation for parameter descriptions
- **WHEN** command parameters are registered
- **THEN** the Translator SHALL provide translations for all `@app_commands.describe()` values

### Requirement: Command name stability
Slash command `name` values SHALL NOT be localized to preserve routing stability.

#### Scenario: Command name remains constant
- **WHEN** the bot registers commands with localization
- **THEN** the command `name` field SHALL remain in its original ASCII form (e.g., "daily", "problem", "config")

#### Scenario: Only description localized
- **WHEN** Discord displays a command in a user's locale
- **THEN** only the description and parameter descriptions SHALL change, not the command name

### Requirement: Translation source from locale files
The Translator SHALL read command metadata translations from the same JSON locale files used by I18nService.

#### Scenario: Shared translation keys
- **WHEN** the Translator needs a command description
- **THEN** it SHALL look up the key in the `commands` namespace of the locale files

#### Scenario: Fallback for missing command translations
- **WHEN** a command description key is missing in the target locale
- **THEN** the Translator SHALL fall back to the zh-TW value
