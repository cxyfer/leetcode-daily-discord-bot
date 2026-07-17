## ADDED Requirements

### Requirement: Manual additional daily command surface
The bot SHALL expose a localized `/daily_extra` slash command with required `source`, optional `date`, and optional `public` parameters. The `source` parameter SHALL be constrained to the Discord choices `sheep` and `0x3f`; `date` SHALL use `YYYY-MM-DD` when present; and `public` SHALL default to `false`.

#### Scenario: Query today's Sheep daily
- **WHEN** a user runs `/daily_extra source:sheep` without a date
- **THEN** the bot SHALL request the current Sheep daily challenge from oj-api-rs

#### Scenario: Query a dated 0x3f daily
- **WHEN** a user runs `/daily_extra source:0x3f date:2026-06-09`
- **THEN** the bot SHALL request the 0x3f daily challenge for `2026-06-09`

#### Scenario: Command source choices
- **WHEN** Discord presents the `source` parameter for `/daily_extra`
- **THEN** the available choices SHALL be exactly `sheep` and `0x3f`

#### Scenario: Existing daily entry points remain unchanged
- **WHEN** `/daily_extra` is registered
- **THEN** `/daily` and `/daily_cn` SHALL retain their existing LeetCode domain behavior and parameters

### Requirement: Additional daily source API contract
The bot SHALL retrieve additional-source daily data through `GET /api/v1/daily` using `source={sheep|0x3f}` and optional `date`, without sending a LeetCode `domain`. It SHALL preserve the returned `{date, source, problems}` envelope and the complete upstream problem order.

#### Scenario: Additional source request parameters
- **WHEN** the bot fetches `/daily_extra source:sheep date:2026-06-02`
- **THEN** the API request SHALL contain `source=sheep` and `date=2026-06-02`
- **AND** the request SHALL NOT contain `domain`

#### Scenario: Multiple problems preserve upstream order
- **WHEN** oj-api-rs returns an ordered `problems` array with two or more problems
- **THEN** the daily payload and displayed overview SHALL retain every returned problem in that order

#### Scenario: LeetCode v0.4 compatibility remains bounded
- **WHEN** an existing `/daily` or `/daily_cn` request receives the oj-api-rs v0.4 flat response
- **THEN** the existing LeetCode normalization SHALL continue to wrap it in the current daily envelope
- **AND** `/daily_extra` SHALL NOT add a legacy flat-response fallback for additional sources

### Requirement: Single and multiple problem presentation
The command SHALL render a valid one-problem daily envelope as a full problem card and a valid multi-problem envelope as a localized ordered overview. Both presentations SHALL identify the selected daily source and resolved date.

#### Scenario: Single additional daily problem
- **WHEN** oj-api-rs returns exactly one problem for `/daily_extra`
- **THEN** the bot SHALL send that problem's full source-aware card and existing problem action view
- **AND** the card footer SHALL identify the additional daily source and resolved date

#### Scenario: Multiple additional daily problems
- **WHEN** oj-api-rs returns between 2 and 25 button-safe problems for `/daily_extra`
- **THEN** the bot SHALL send one overview containing every problem in upstream order
- **AND** the overview title or footer SHALL identify the additional daily source and resolved date
- **AND** the overview SHALL contain one detail button per displayed problem in the same order

#### Scenario: Detail buttons reuse the unified protocol
- **WHEN** a multi-problem overview creates a problem detail button
- **THEN** its custom id SHALL use `problem|{problem.source}|{problem.id}|view`
- **AND** no daily-specific interaction state or custom-id format SHALL be required

### Requirement: Multi-user detail privacy
Every full problem detail opened from a `/daily_extra` overview SHALL be sent as an ephemeral response to the clicking user. The handler SHALL NOT edit or replace the original overview.

#### Scenario: Detail from a private overview
- **WHEN** a user clicks a problem button on an ephemeral `/daily_extra` overview
- **THEN** the bot SHALL send that problem's full card ephemerally to that user

#### Scenario: Detail from a public overview
- **WHEN** a user clicks a problem button on a public `/daily_extra` overview
- **THEN** the bot SHALL still send the full problem card ephemerally to the clicking user
- **AND** the public overview SHALL remain unchanged

#### Scenario: Independent concurrent clicks
- **WHEN** two users click different problem buttons on the same public overview
- **THEN** each user SHALL receive an independent ephemeral problem card
- **AND** neither interaction SHALL overwrite the other user's response or the overview

### Requirement: Complete and safe overview interaction
The bot SHALL attach a `/daily_extra` overview view only when every displayed problem can be represented completely within Discord's 25-button, label, row, custom-id, embed-field, and total-embed limits. It SHALL reject an unsafe payload with a localized error instead of attaching a partial button set.

#### Scenario: Exact 25-problem boundary
- **WHEN** an additional daily payload contains exactly 25 button-safe problems
- **THEN** the overview SHALL contain exactly 25 buttons arranged with at most 5 buttons per row and at most 5 rows

#### Scenario: More than 25 problems
- **WHEN** an additional daily payload contains more than 25 problems
- **THEN** the command SHALL send a localized payload-limit error
- **AND** it SHALL NOT send a partial overview containing only the first 25 buttons

#### Scenario: Unsafe routing fields
- **WHEN** any returned problem lacks a non-empty `source` or `id`, contains the custom-id separator in either routing segment, or would exceed a Discord label/custom-id limit
- **THEN** the command SHALL send a localized payload error
- **AND** it SHALL NOT send a partial overview

#### Scenario: Oversized overview embed
- **WHEN** the generated overview exceeds a Discord embed field or total-length limit
- **THEN** the command SHALL send a localized payload error
- **AND** it SHALL NOT send the invalid overview

#### Scenario: Existing generic overview keeps its LeetCode source default
- **WHEN** an existing `/problem` multi-problem response omits `source`
- **THEN** its overview buttons SHALL continue to route with `leetcode` as the default source
- **AND** `/daily_extra` SHALL continue to require an explicit source on every returned problem

### Requirement: Visibility, localization, and error handling
The initial `/daily_extra` response SHALL be ephemeral by default and public only when `public=true`. Command metadata and all user-facing text SHALL be available in zh-TW, en-US, and zh-CN through the existing locale system.

#### Scenario: Default private initial response
- **WHEN** a user runs `/daily_extra` without `public=true`
- **THEN** the command SHALL defer and send its initial card, overview, or error ephemerally

#### Scenario: Public initial response
- **WHEN** a user runs `/daily_extra public:true`
- **THEN** the command SHALL defer and send its initial card or overview publicly

#### Scenario: Invalid date format
- **WHEN** a user supplies a date that does not match `YYYY-MM-DD`
- **THEN** the command SHALL send the existing localized date-format error with the requested visibility
- **AND** it SHALL NOT call the API

#### Scenario: Source/date unavailable
- **WHEN** oj-api-rs returns `404` for the requested additional source and date
- **THEN** the command SHALL send a localized not-found response identifying the request context

#### Scenario: Additional daily data is processing
- **WHEN** oj-api-rs returns `202` with `fetching` or `ingestion_required` status
- **THEN** the command SHALL send the existing localized processing response

#### Scenario: API failure classes
- **WHEN** the request fails because of a network error, rate limit, or other API error
- **THEN** the command SHALL use the existing localized API error mapping

#### Scenario: Locale key parity
- **WHEN** `/daily_extra` locale keys are added
- **THEN** zh-TW, en-US, and zh-CN SHALL expose the same key set within Discord's metadata and message length limits

### Requirement: Manual-only first-stage scope
The `/daily_extra` capability SHALL be available only through explicit user invocation in this change and SHALL NOT alter scheduled daily delivery, guild settings, or persistence.

#### Scenario: Scheduled delivery remains LeetCode-only
- **WHEN** existing scheduled daily jobs execute after `/daily_extra` is deployed
- **THEN** they SHALL retain their current LeetCode domain behavior and SHALL NOT schedule Sheep or 0x3f delivery

#### Scenario: No configuration or database migration
- **WHEN** `/daily_extra` is deployed
- **THEN** no guild configuration field, database table, or migration SHALL be added for additional daily sources

## PBT Properties

### Property: Ordered complete overview
- **INVARIANT**: Every accepted multi-problem payload yields exactly one overview button for every displayed problem in the same order
- **FALSIFICATION**: Generate valid problem lists of size 2 through 25 and compare payload order, overview line order, button labels, and custom ids

### Property: All-or-nothing daily detail affordance
- **INVARIANT**: A `/daily_extra` multi-problem result is either rendered with a complete safe button set or rejected without a partial overview
- **FALSIFICATION**: Generate lists exceeding 25 items or containing one unsafe routing segment and assert no subset of buttons is sent

### Property: Selected detail isolation
- **INVARIANT**: The visibility of the initial overview never changes the ephemeral visibility of a selected problem detail
- **FALSIFICATION**: Exercise private and public initial responses with multiple simulated clickers and assert every `view` follow-up is ephemeral and the original response is never edited
