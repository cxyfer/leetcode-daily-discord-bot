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

#### Scenario: Source-aware multi-problem overview
- **WHEN** all problems in a multi-problem `/problem` query come from the same supported source
- **THEN** the overview embed SHALL display that source label and the detail buttons SHALL use source-aware difficulty emoji mappings when available

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

### Requirement: Unified config command
The `/config` command SHALL allow server admins to view, update, and reset all server configuration. It dispatches three modes based on parameters: **show** (no params), **reset** (`reset:True` alone), and **update** (any setting params).

#### Scenario: Show mode — server has settings
- **WHEN** an admin runs `/config` without any parameters and the server has existing settings
- **THEN** the bot SHALL display the current settings using `create_settings_embed()` as an ephemeral message

#### Scenario: Show mode — server has no settings
- **WHEN** an admin runs `/config` without any parameters and the server has no settings
- **THEN** the bot SHALL respond with ephemeral text: "尚未設定 LeetCode 每日挑戰頻道。使用 `/config channel:<頻道>` 開始設定。"

#### Scenario: Update success response
- **WHEN** any `/config` update succeeds
- **THEN** the bot SHALL respond with `content="✅ 設定已更新"` and an embed from `create_settings_embed()` reflecting the persisted state, as an ephemeral message

#### Scenario: Reset mode — server has settings
- **WHEN** an admin runs `/config reset:True` without other params and the server has existing settings
- **THEN** the bot SHALL send an ephemeral message containing a settings summary embed and two buttons labeled "確認重置" (danger style) and "取消" (secondary style)

#### Scenario: Reset mode — server has no settings
- **WHEN** an admin runs `/config reset:True` and the server has no settings
- **THEN** the bot SHALL respond with ephemeral text: "此伺服器尚未設定，無需重置。"

#### Scenario: Reset mutual exclusion
- **WHEN** an admin runs `/config reset:True` together with any of `channel`, `role`, `time`, `timezone`, or `clear_role`
- **THEN** the bot SHALL reject with ephemeral text: "`reset` 不可與其他設定參數同時使用。"

#### Scenario: Mode dispatch order
- **WHEN** `/config` is invoked
- **THEN** the bot SHALL evaluate in order: reset conflict check → show mode check → input validation → update logic

#### Scenario: First-time setup with all parameters
- **WHEN** an admin with `manage_guild` permission runs `/config channel:#general time:08:00 timezone:UTC+8`
- **THEN** the bot SHALL save all settings and trigger schedule creation, responding with `content="✅ 設定已更新"` and a settings embed

#### Scenario: Partial update
- **WHEN** an admin runs `/config time:09:00` on a server with existing settings
- **THEN** the bot SHALL update only `post_time` to `09:00`, preserving all other settings, and trigger reschedule

#### Scenario: First-time setup without channel
- **WHEN** an admin runs `/config time:08:00` on a server with no existing settings
- **THEN** the bot SHALL respond with an ephemeral error stating channel is required for first-time setup, with usage example

#### Scenario: Atomic validation failure
- **WHEN** an admin runs `/config time:08:00 timezone:InvalidZone`
- **THEN** the bot SHALL reject the entire request without updating any field, returning the timezone validation error

#### Scenario: Permission check
- **WHEN** a user without `manage_guild` permission runs `/config`
- **THEN** the bot SHALL respond with ephemeral text: "您需要「管理伺服器」權限才能使用此指令。"

#### Scenario: Guild-only enforcement
- **WHEN** a user runs `/config` in a DM
- **THEN** the bot SHALL respond indicating this command cannot be used in DMs

#### Scenario: Reset parameter describe text
- **WHEN** the `reset` parameter is displayed in Discord's command UI
- **THEN** the describe text SHALL be "重置所有設定並停止排程（需確認）"

### Requirement: Role clearing via config command
The `/config` command SHALL support clearing the notification role via a `clear_role` boolean parameter.

#### Scenario: Clear existing role
- **WHEN** an admin runs `/config clear_role:True` on a server with a role set
- **THEN** the bot SHALL set `role_id` to NULL in the database and display "未設定" for role in the success response

#### Scenario: Clear role with simultaneous role parameter
- **WHEN** an admin runs `/config role:@SomeRole clear_role:True`
- **THEN** the bot SHALL reject with an ephemeral error indicating `role` and `clear_role` are mutually exclusive

#### Scenario: Clear role when no role set
- **WHEN** an admin runs `/config clear_role:True` on a server with no role configured
- **THEN** the bot SHALL succeed without error (idempotent), keeping role as NULL

### Requirement: Time format auto-padding
The `/config` command SHALL accept single-digit hour format and normalize to zero-padded `HH:MM` before storage.

#### Scenario: Single-digit hour normalization
- **WHEN** an admin runs `/config time:8:00`
- **THEN** the bot SHALL store `08:00` in the database

#### Scenario: Already padded time
- **WHEN** an admin runs `/config time:08:00`
- **THEN** the bot SHALL store `08:00` in the database (no change)

#### Scenario: Invalid time rejection
- **WHEN** an admin runs `/config time:24:00` or `/config time:12:60`
- **THEN** the bot SHALL reject with an ephemeral error showing valid format examples

### Requirement: Timezone autocomplete
The `/config` command SHALL provide autocomplete suggestions for the `timezone` parameter.

#### Scenario: Empty input autocomplete
- **WHEN** the user opens the timezone autocomplete without typing
- **THEN** the bot SHALL show popular options including `UTC`, common UTC offsets (UTC+8, UTC+9, UTC-5, etc.), and popular IANA zones (Asia/Taipei, Asia/Tokyo, America/New_York, Europe/London)

#### Scenario: Filtered autocomplete
- **WHEN** the user types "UTC+8" in the timezone field
- **THEN** the bot SHALL filter suggestions to show matching entries (e.g., `UTC+8`, `UTC+8:30`)

#### Scenario: IANA name autocomplete
- **WHEN** the user types "Asia" in the timezone field
- **THEN** the bot SHALL filter suggestions to show matching IANA zones (e.g., Asia/Taipei, Asia/Tokyo, Asia/Shanghai)

### Requirement: Random problem command
The `/random` command SHALL fetch and display a random LeetCode problem with optional filtering.

#### Scenario: Fetch random problem without filters
- **WHEN** a user runs `/random` without any filter parameters
- **THEN** the bot SHALL display a random problem from the entire LeetCode problem set with problem info, difficulty, tags, and interactive buttons

#### Scenario: Fetch random problem with difficulty filter
- **WHEN** a user runs `/random difficulty:Medium`
- **THEN** the bot SHALL display a random problem that has difficulty "Medium"

#### Scenario: Fetch random problem with tags filter
- **WHEN** a user runs `/random tags:Array`
- **THEN** the bot SHALL display a random problem that includes the "Array" tag

#### Scenario: Fetch random problem with rating range
- **WHEN** a user runs `/random rating_min:1500 rating_max:2000`
- **THEN** the bot SHALL display a random problem with rating between 1500 and 2000 (inclusive)

#### Scenario: Public toggle
- **WHEN** a user runs `/random` with the `public` parameter set to True
- **THEN** the response SHALL be visible to all users in the channel instead of ephemeral

#### Scenario: No matching problems
- **WHEN** a user runs `/random` with filter conditions that match no problems
- **THEN** the bot SHALL display an ephemeral error message showing the applied filter summary (e.g., "沒有找到符合 difficulty:Hard, tags:Array, rating:1500-2000 的題目")

### Requirement: Rating parameter validation
The `/random` command SHALL validate and normalize rating parameters.

#### Scenario: Rating min greater than max
- **WHEN** a user runs `/random rating_min:2000 rating_max:1500`
- **THEN** the bot SHALL automatically swap the values and use rating_min=1500, rating_max=2000

#### Scenario: Single rating bound
- **WHEN** a user runs `/random rating_min:1500` without rating_max
- **THEN** the bot SHALL use rating_min=1500 with no upper bound

#### Scenario: Rating boundary inclusive
- **WHEN** a user runs `/random rating_min:1500 rating_max:1500`
- **THEN** the bot SHALL display problems with rating exactly 1500

### Requirement: API client random problem method
The `OjApiClient` SHALL provide a `get_random_problem()` method that performs filtered random selection.

#### Scenario: Two-call random selection
- **WHEN** `get_random_problem()` is called with filters
- **THEN** the method SHALL first fetch the total count of matching problems, then fetch one random problem from the filtered set

#### Scenario: Zero results handling
- **WHEN** `get_random_problem()` is called and the API returns total count of 0
- **THEN** the method SHALL return a domain-level no-match result (not an API error)

#### Scenario: API error propagation
- **WHEN** `get_random_problem()` encounters API errors (429, timeout, network failure)
- **THEN** the method SHALL propagate standard error types (ApiRateLimitError, ApiNetworkError, ApiProcessingError)

### Requirement: UI component reuse
The `/random` command SHALL reuse existing UI components for consistent display.

#### Scenario: Problem embed format
- **WHEN** a random problem is successfully fetched
- **THEN** the bot SHALL use `create_problem_embed()` to generate the embed with difficulty color, tags, and rating

#### Scenario: Interactive buttons
- **WHEN** a random problem is displayed
- **THEN** the bot SHALL use `create_problem_view()` to generate buttons for description, translation, inspiration, and similar problems

#### Scenario: Button interaction routing
- **WHEN** a user clicks any button on a random problem
- **THEN** the interaction SHALL be routed through `InteractionHandlerCog` using the standard `problem|{source}|{id}|{action}` format

