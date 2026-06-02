## MODIFIED Requirements

### Requirement: Daily challenge command
The `/daily` command SHALL fetch and display the current daily challenge from LeetCode with user-facing text localized to the resolved locale, reusing in-flight or cached daily payload data where available without suppressing valid user responses.

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

#### Scenario: Concurrent identical daily data requests
- **WHEN** multiple users run `/daily` for the same domain/date while daily payload data is already in flight
- **THEN** the bot SHALL reuse the in-flight daily payload data and still send each valid interaction its own response

#### Scenario: Cached daily data reuse
- **WHEN** a user runs `/daily` for a domain/date whose daily payload is still within the short-lived cache window
- **THEN** the bot SHALL render the response from cached payload data without refetching the same daily challenge and history data
