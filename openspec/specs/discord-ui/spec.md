# discord-ui Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Centralized embed creation
The system SHALL provide centralized functions for creating Discord embeds with consistent styling.

#### Scenario: Problem embed
- **WHEN** a problem embed is created
- **THEN** it SHALL include problem title, difficulty, tags, rating, and use difficulty-based color coding with emoji prefixes

#### Scenario: Submission embed
- **WHEN** a submission embed is created
- **THEN** it SHALL include difficulty, rating, acceptance rate, and tags

#### Scenario: Problems overview embed
- **WHEN** multiple problems are queried at once
- **THEN** the system SHALL create an overview embed listing all problems with detail buttons for each

#### Scenario: Settings embed
- **WHEN** server settings are displayed
- **THEN** the system SHALL create a settings embed showing channel, role, post time, and timezone

#### Scenario: Similar results embed
- **WHEN** similar problems are displayed
- **THEN** the system SHALL create a similar results embed with rewritten query or base problem context, numbered result list with source-aware difficulty emoji, problem ID, title, link, source label, and similarity score

### Requirement: Consistent color and emoji mappings
The system SHALL use predefined color codes and emoji mappings for difficulty levels and problem attributes.

#### Scenario: Difficulty color coding
- **WHEN** an embed is created for a problem
- **THEN** the embed color SHALL match the difficulty level (Easy=green, Medium=orange, Hard=red)

#### Scenario: Source-aware difficulty emoji
- **WHEN** a problem from any source is displayed
- **THEN** the system SHALL use source-specific difficulty emoji mappings (LeetCode: Easy/Medium/Hard → 🟢🟡🔴, Luogu: 8-tier color scale, other sources: 🧩)

#### Scenario: Field splitting for readability
- **WHEN** an embed field contains multiple items
- **THEN** the system SHALL split items into multiple fields with maximum 5 items per field and enforce 1024-character limit per field value

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
The system SHALL create button views with persistent custom_ids that survive bot restarts.

#### Scenario: Button custom_id format
- **WHEN** buttons are created for a problem
- **THEN** custom_ids SHALL follow the format `{PREFIX}_{problem_id}_{domain}` or `{PREFIX}|{source}|{problem_id}`

#### Scenario: Button within character limit
- **WHEN** a custom_id is generated
- **THEN** it SHALL not exceed 100 characters

#### Scenario: Button row layout
- **WHEN** multiple buttons are created
- **THEN** the system SHALL arrange them with a maximum of 5 buttons per row

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

