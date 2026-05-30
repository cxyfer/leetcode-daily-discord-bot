# discord-ui Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Centralized embed creation
The system SHALL provide centralized functions for creating Discord embeds with consistent styling and localized user-facing strings.

#### Scenario: Problem embed
- **WHEN** a problem embed is created
- **THEN** it SHALL include problem title, difficulty, tags, rating, and difficulty-based styling with field names and footer text resolved for the active locale

#### Scenario: Submission embed
- **WHEN** a submission embed is created
- **THEN** it SHALL include difficulty, rating, acceptance rate, and tags with field names resolved for the active locale

#### Scenario: Problems overview embed
- **WHEN** multiple problems are queried at once
- **THEN** the system SHALL create a localized overview embed listing all problems with detail buttons for each

#### Scenario: Settings embed
- **WHEN** server settings are displayed
- **THEN** the system SHALL create a localized settings embed showing channel, role, post time, timezone, and language

#### Scenario: Similar results embed
- **WHEN** similar problems are displayed
- **THEN** the system SHALL create a localized similar results embed while preserving problem IDs, source labels, links, and similarity scores

### Requirement: Consistent color and emoji mappings
The system SHALL use predefined color codes and emoji mappings for difficulty levels and problem attributes, and these visual mappings SHALL NOT be localized.

#### Scenario: Difficulty color coding
- **WHEN** an embed is created for a LeetCode problem
- **THEN** the embed color SHALL match the difficulty level

#### Scenario: Source-aware difficulty emoji
- **WHEN** a problem from any source is displayed
- **THEN** the system SHALL use source-specific difficulty emoji mappings independent of locale

### Requirement: Discord limit enforcement
The system SHALL enforce Discord API limits when constructing embeds and messages.

#### Scenario: Field value truncation
- **WHEN** an embed field value exceeds 1024 characters
- **THEN** the system SHALL truncate it with an ellipsis indicator

#### Scenario: Total embed size limit
- **WHEN** the total embed content approaches 6000 characters
- **THEN** the system SHALL ensure the embed stays within Discord's limit

#### Scenario: Message content limit
- **WHEN** message content exceeds 2000 characters
- **THEN** the system SHALL truncate or split the content

### Requirement: Persistent button views
The system SHALL create button views with persistent custom_ids and localized labels that survive bot restarts.

#### Scenario: Problem action button labels
- **WHEN** buttons are created for a problem
- **THEN** labels for description, translate, inspiration, and similar actions SHALL be resolved for the active locale

#### Scenario: Config reset button labels
- **WHEN** config reset confirmation buttons are created
- **THEN** confirm and cancel labels SHALL be resolved for the active locale

#### Scenario: Button custom_id format
- **WHEN** buttons are created for a problem
- **THEN** custom_ids SHALL follow the stable `problem|{source}|{problem_id}|{action}` format regardless of locale

### Requirement: Localized button labels
All interactive buttons SHALL use labels resolved via `t()` for the active locale.

#### Scenario: Problem view buttons
- **WHEN** a problem view is created
- **THEN** the button labels for description, translate, inspire, and similar SHALL be resolved via `t()` based on the active locale

#### Scenario: Config reset buttons
- **WHEN** a config reset confirmation view is created
- **THEN** the confirm and cancel button labels SHALL be resolved via `t()`

### Requirement: Localized embed footers
All embed footers SHALL use text resolved via `t()` for the active locale.

#### Scenario: Problem footer
- **WHEN** a problem embed footer is rendered
- **THEN** it SHALL display the localized "LeetCode Problem" or "LeetCode Daily Challenge" text

#### Scenario: Submission footer
- **WHEN** a submission embed footer is rendered
- **THEN** it SHALL display the localized page indicator (e.g., "Problem 1 of 5")

### Requirement: Similar-result detail buttons align with the displayed result list
The system SHALL render similar-result detail buttons as a persistent Discord view that stays aligned with the displayed result list whenever the response is button-safe.

#### Scenario: Button labels use problem IDs
- **WHEN** detail buttons are attached to a similar-result response
- **THEN** each button label SHALL be the corresponding problem ID from the displayed result

#### Scenario: Button order matches result order
- **WHEN** multiple similar-result detail buttons are attached
- **THEN** the buttons SHALL appear in the same order as the displayed similar results in the embed

#### Scenario: Button rows stay within Discord layout limits
- **WHEN** a similar-result response attaches up to 25 detail buttons
- **THEN** the view SHALL place at most 5 buttons in each row and at most 5 rows total

### Requirement: Similar-result responses avoid partial interactive affordances
The system SHALL keep similar-result responses embed-only when the displayed result list cannot be represented completely and safely as detail buttons.

#### Scenario: Overflow response remains embed-only
- **WHEN** a similar-result response contains more than 25 displayed results
- **THEN** the system SHALL not attach only the first 25 buttons and SHALL keep the response embed-only

#### Scenario: Invalid-item response remains embed-only
- **WHEN** any displayed similar result cannot safely generate the existing problem-detail custom_id
- **THEN** the system SHALL keep the response embed-only rather than mixing clickable and non-clickable listed items

### Requirement: Daily challenge posting
The `send_daily_challenge()` function SHALL compose and send the daily challenge message using localized UI text.

#### Scenario: Send daily challenge
- **WHEN** `send_daily_challenge()` is called with a channel, challenge data, and locale context
- **THEN** the system SHALL create a localized embed, attach localized interactive buttons, and optionally mention a role

### Requirement: Ephemeral error responses
Error messages to users SHALL be sent as localized ephemeral messages to avoid channel clutter.

#### Scenario: Error response
- **WHEN** an interaction results in an error
- **THEN** the error message SHALL be localized and visible only to the requesting user


## PBT Properties

### Property: Button order preservation
- **INVARIANT**: Detail-button order always matches the displayed result order in the embed
- **FALSIFICATION**: Generate arbitrary valid result lists and assert that button labels and custom_ids preserve the same ordering as the rendered result list

### Property: Layout boundedness
- **INVARIANT**: No similar-result detail view contains more than 5 buttons in any row or more than 5 rows total
- **FALSIFICATION**: Generate valid result counts from 1 to 25 and assert each button row index stays within `0..4` with at most 5 buttons per row

### Requirement: Daily challenge posting
The `send_daily_challenge()` function SHALL compose and send the daily challenge message to a channel.

#### Scenario: Send daily challenge
- **WHEN** `send_daily_challenge()` is called with a channel and challenge data
- **THEN** the system SHALL create an embed with problem info, attach interactive buttons, and optionally mention a role

### Requirement: Ephemeral error responses
Error messages to users SHALL be sent as ephemeral messages to avoid channel clutter.

#### Scenario: Error response
- **WHEN** an interaction results in an error
- **THEN** the error message SHALL be sent as an ephemeral response visible only to the requesting user
