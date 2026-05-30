## MODIFIED Requirements

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
