## MODIFIED Requirements

### Requirement: Daily challenge command
The `/daily` command SHALL fetch and display the current daily challenge from LeetCode, with all UI text localized.

#### Scenario: Fetch today's challenge
- **WHEN** a user runs `/daily`
- **THEN** the bot SHALL display the daily challenge embed with localized UI text

#### Scenario: Fetch challenge by date
- **WHEN** a user runs `/daily` with a date parameter (YYYY-MM-DD format)
- **THEN** the bot SHALL display the daily challenge for that specific date with localized UI text

#### Scenario: CN domain support
- **WHEN** a user runs `/daily_cn`
- **THEN** the bot SHALL fetch the daily challenge from leetcode.cn instead of leetcode.com

#### Scenario: Public toggle
- **WHEN** a user runs `/daily` with the `public` parameter set to True
- **THEN** the response SHALL be visible to all users in the channel instead of ephemeral

### Requirement: Problem lookup command
The `/problem` command SHALL fetch and display specific problems by ID, URL, or slug, with all UI text localized.

#### Scenario: Lookup by problem number
- **WHEN** a user runs `/problem` with a numeric ID
- **THEN** the bot SHALL display the problem embed with localized details and interactive buttons

## ADDED Requirements

### Requirement: Localized command descriptions
All slash command descriptions and parameter descriptions SHALL be localized via the discord.py Translator.

#### Scenario: Command description in user locale
- **WHEN** a user views the command picker in en-US locale
- **THEN** all command and parameter descriptions SHALL display in English

#### Scenario: Command description in zh-TW locale
- **WHEN** a user views the command picker in zh-TW locale
- **THEN** all command and parameter descriptions SHALL display in Traditional Chinese

### Requirement: Localized validation and error messages
All validation and error messages in slash commands SHALL be resolved via `t()`.

#### Scenario: Invalid date format
- **WHEN** a user provides an invalid date format to `/daily`
- **THEN** the bot SHALL respond with a localized error message

#### Scenario: Permission check failure
- **WHEN** a user without "Manage Server" permission runs `/config`
- **THEN** the bot SHALL respond with a localized permission error

#### Scenario: DM restriction
- **WHEN** a user runs `/config` in a DM
- **THEN** the bot SHALL respond with a localized DM restriction error

### Requirement: Language configuration via /config
The `/config` command SHALL accept a `language` parameter with Choice list for setting the guild language.

#### Scenario: Set guild language
- **WHEN** a user runs `/config language:en-US`
- **THEN** the bot SHALL update `server_settings.language` to "en-US" and confirm with a localized message

#### Scenario: Language choice list
- **WHEN** a user types `/config language:`
- **THEN** Discord SHALL display a choice list with "zh-TW", "en-US", and "zh-CN"

#### Scenario: View current language setting
- **WHEN** a user runs `/config` without the language parameter
- **THEN** the settings embed SHALL display the current language setting

### Requirement: Localized API error handling
All API error messages in slash commands SHALL be resolved via `t()` instead of hardcoded strings.

#### Scenario: API processing error
- **WHEN** an `ApiProcessingError` occurs
- **THEN** the bot SHALL respond with `t("errors.api.processing", locale)`

#### Scenario: API network error
- **WHEN** an `ApiNetworkError` occurs
- **THEN** the bot SHALL respond with `t("errors.api.network", locale)`

#### Scenario: API rate limit error
- **WHEN** an `ApiRateLimitError` occurs
- **THEN** the bot SHALL respond with `t("errors.api.rate_limit", locale)`
