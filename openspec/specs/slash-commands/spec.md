# slash-commands Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Daily challenge command
The `/daily` command SHALL fetch and display the current daily challenge from LeetCode.

#### Scenario: Fetch today's challenge
- **WHEN** a user runs `/daily`
- **THEN** the bot SHALL display the daily challenge embed with problem info, difficulty, tags, and interactive buttons

#### Scenario: Fetch challenge by date
- **WHEN** a user runs `/daily` with a date parameter (YYYY-MM-DD format)
- **THEN** the bot SHALL display the daily challenge for that specific date

#### Scenario: CN domain support
- **WHEN** a user runs `/daily_cn`
- **THEN** the bot SHALL fetch the daily challenge from leetcode.cn instead of leetcode.com

#### Scenario: Public toggle
- **WHEN** a user runs `/daily` with the `public` parameter set to True
- **THEN** the response SHALL be visible to all users in the channel instead of ephemeral

### Requirement: Problem lookup command
The `/problem` command SHALL fetch and display specific problems by ID, URL, or slug.

#### Scenario: Lookup by problem number
- **WHEN** a user runs `/problem` with a numeric ID
- **THEN** the bot SHALL display the problem embed with details and interactive buttons

#### Scenario: Lookup by URL
- **WHEN** a user runs `/problem` with a LeetCode URL
- **THEN** the bot SHALL parse the URL, detect the source, and display the problem

#### Scenario: Multi-source support
- **WHEN** a user provides a problem from AtCoder, Codeforces, Luogu, UVA, or SPOJ
- **THEN** the bot SHALL detect the source and display the problem accordingly

#### Scenario: Multi-problem query
- **WHEN** a user provides multiple problem IDs (comma or space separated, up to 20)
- **THEN** the bot SHALL display an overview embed with detail buttons for each problem

#### Scenario: Custom title and message
- **WHEN** a user provides `title` and/or `message` parameters
- **THEN** the bot SHALL use the custom title for the overview embed and include the message as additional context

#### Scenario: Explicit source parameter
- **WHEN** a user provides the `source` parameter
- **THEN** the bot SHALL use the specified source instead of auto-detecting

### Requirement: Recent submissions command
The `/recent` command SHALL display a user's recent accepted submissions on LeetCode.

#### Scenario: Display recent submissions
- **WHEN** a user runs `/recent` with a LeetCode username
- **THEN** the bot SHALL display the user's recent accepted submissions (default limit 20, max 50)

#### Scenario: Submission pagination
- **WHEN** submissions are displayed with navigation buttons
- **THEN** the user SHALL be able to navigate through submissions using previous/next buttons

### Requirement: Server settings commands
The bot SHALL provide commands to configure per-server settings.

#### Scenario: Set notification channel
- **WHEN** an admin runs `/set_channel` with a channel
- **THEN** the bot SHALL save the channel and trigger schedule creation/update

#### Scenario: Set mention role
- **WHEN** an admin runs `/set_role` with a role
- **THEN** the bot SHALL save the role for daily challenge mentions

#### Scenario: Set post time
- **WHEN** an admin runs `/set_post_time` with a time (HH:MM)
- **THEN** the bot SHALL save the time and reschedule the daily job

#### Scenario: Set timezone
- **WHEN** an admin runs `/set_timezone` with a valid timezone
- **THEN** the bot SHALL save the timezone and reschedule the daily job

#### Scenario: Show settings
- **WHEN** a user runs `/show_settings`
- **THEN** the bot SHALL display all current server settings

#### Scenario: Remove channel
- **WHEN** an admin runs `/remove_channel`
- **THEN** the bot SHALL remove the notification channel and cancel the scheduled job

### Requirement: Channel prerequisite
Server settings that depend on a channel (role, post_time, timezone) SHALL require a channel to be set first.

#### Scenario: Setting without channel
- **WHEN** an admin tries to set post_time without a channel configured
- **THEN** the bot SHALL respond with an error indicating a channel must be set first

