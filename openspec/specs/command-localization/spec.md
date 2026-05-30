# command-localization Specification

## Purpose
TBD - created by applying change sync-openspec-specs-after-v2-0-2. Update Purpose after archive.
## Requirements
### Requirement: discord.py Translator implementation
The system SHALL implement a `discord.app_commands.Translator` integration for slash command metadata localization.

#### Scenario: Translator registration at startup
- **WHEN** the bot starts
- **THEN** it SHALL call `bot.tree.set_translator(...)` before syncing slash commands

#### Scenario: Command description translations
- **WHEN** slash commands are synced
- **THEN** the translator SHALL provide command description translations for zh-TW, en-US, and zh-CN

#### Scenario: Parameter description translations
- **WHEN** command parameters are registered
- **THEN** the translator SHALL provide parameter description translations for zh-TW, en-US, and zh-CN

### Requirement: Command name stability
Slash command names SHALL remain stable and SHALL NOT be localized.

#### Scenario: Command name remains constant
- **WHEN** the bot registers localized slash commands
- **THEN** command `name` values such as `daily`, `problem`, `config`, and `random` SHALL remain unchanged

#### Scenario: Only metadata is localized
- **WHEN** Discord displays a command in a user's locale
- **THEN** only command descriptions and parameter descriptions SHALL change language

### Requirement: Translation source from locale files
The command translator SHALL read command metadata translations from the same locale files used by I18nService.

#### Scenario: Shared command metadata keys
- **WHEN** the translator needs a command or parameter description
- **THEN** it SHALL look up the corresponding key from the command metadata namespace in the locale files

#### Scenario: Missing command translation fallback
- **WHEN** a command metadata translation is missing in the target locale
- **THEN** the translator SHALL fall back to the zh-TW value
