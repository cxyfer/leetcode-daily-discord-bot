## MODIFIED Requirements

### Requirement: Daily challenge command
The `/daily` command SHALL fetch and display the current daily challenge from LeetCode with user-facing text localized to the resolved locale.

#### Scenario: Fetch today's challenge
- **WHEN** a user runs `/daily`
- **THEN** the bot SHALL display the daily challenge embed with localized UI text, problem info, difficulty, tags, and interactive buttons

#### Scenario: Fetch challenge by date
- **WHEN** a user runs `/daily` with a date parameter in YYYY-MM-DD format
- **THEN** the bot SHALL display the daily challenge for that date with localized UI text

#### Scenario: CN domain support
- **WHEN** a user runs `/daily_cn`
- **THEN** the bot SHALL fetch the daily challenge from leetcode.cn instead of leetcode.com

#### Scenario: Public toggle
- **WHEN** a user runs `/daily` with the `public` parameter set to True
- **THEN** the response SHALL be visible to all users in the channel instead of ephemeral

### Requirement: Problem lookup command
The `/problem` command SHALL fetch and display specific problems by ID, URL, or slug with user-facing text localized to the resolved locale.

#### Scenario: Lookup by problem number
- **WHEN** a user runs `/problem` with a numeric ID
- **THEN** the bot SHALL display the problem embed with localized details and interactive buttons

#### Scenario: Multi-source support
- **WHEN** a user provides a problem from AtCoder, Codeforces, Luogu, UVA, or SPOJ
- **THEN** the bot SHALL detect the source and display the problem with localized UI text

### Requirement: Unified config command
The `/config` command SHALL allow server admins to view, update, and reset all server configuration, including guild language.

#### Scenario: Set guild language
- **WHEN** an admin runs `/config language:en-US`
- **THEN** the bot SHALL update `server_settings.language` to `en-US` and confirm with a localized message

#### Scenario: Language choice list
- **WHEN** a user types `/config language:`
- **THEN** Discord SHALL display a choice list with `zh-TW`, `en-US`, and `zh-CN`

#### Scenario: View current language setting
- **WHEN** an admin runs `/config` without update parameters
- **THEN** the settings embed SHALL display the current language setting with localized field names

#### Scenario: Permission check
- **WHEN** a user without `manage_guild` permission runs `/config`
- **THEN** the bot SHALL respond with a localized permission error

### Requirement: Random problem command
The `/random` command SHALL fetch and display a random problem from the selected source with optional filtering.

#### Scenario: Fetch random problem without filters
- **WHEN** a user runs `/random` without filter parameters
- **THEN** the bot SHALL display a random problem using the default source behavior with localized UI text

#### Scenario: Fetch random problem with source filter
- **WHEN** a user runs `/random source:atcoder`
- **THEN** the bot SHALL request a random problem from the AtCoder source and display it with source-aware UI formatting

#### Scenario: Fetch random problem with all sources
- **WHEN** a user runs `/random source:all`
- **THEN** the bot SHALL request a random problem without restricting the source to a single judge

#### Scenario: Fetch random problem with tags and source
- **WHEN** a user runs `/random source:codeforces tags:dp`
- **THEN** the bot SHALL pass both source and tag filters to the random problem API

#### Scenario: No matching problems
- **WHEN** a user runs `/random` with filter conditions that match no problems
- **THEN** the bot SHALL display a localized ephemeral error message showing the applied filter summary

### Requirement: Localized command descriptions
All slash command descriptions and parameter descriptions SHALL be localized via the command localization translator.

#### Scenario: Command description in user locale
- **WHEN** a user views the command picker in en-US locale
- **THEN** supported command and parameter descriptions SHALL display in English

#### Scenario: Command description in zh-TW locale
- **WHEN** a user views the command picker in zh-TW locale
- **THEN** supported command and parameter descriptions SHALL display in Traditional Chinese

### Requirement: Localized validation and API errors
Slash commands SHALL resolve validation and API error messages through the active locale.

#### Scenario: Invalid date format
- **WHEN** a user provides an invalid date format to `/daily`
- **THEN** the bot SHALL respond with a localized error message

#### Scenario: API processing error
- **WHEN** an `ApiProcessingError` occurs in a slash command
- **THEN** the bot SHALL respond with the localized API processing error message

#### Scenario: API network error
- **WHEN** an `ApiNetworkError` occurs in a slash command
- **THEN** the bot SHALL respond with the localized API network error message
