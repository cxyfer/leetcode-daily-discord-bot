## MODIFIED Requirements

### Requirement: Centralized embed creation
The system SHALL provide centralized functions for creating Discord embeds with consistent styling, using localized strings from the I18nService.

#### Scenario: Problem embed
- **WHEN** a problem embed is created
- **THEN** it SHALL include problem title, difficulty, tags, rating, and use difficulty-based color coding with emoji prefixes, with all UI text (field names, footer, button labels) resolved via `t()` for the active locale

#### Scenario: Submission embed
- **WHEN** a submission embed is created
- **THEN** it SHALL include difficulty, rating, acceptance rate, and tags, with all UI text resolved via `t()`

#### Scenario: Problems overview embed
- **WHEN** multiple problems are queried at once
- **THEN** the system SHALL create an overview embed listing all problems with detail buttons, with all UI text resolved via `t()`

#### Scenario: Settings embed
- **WHEN** server settings are displayed
- **THEN** the system SHALL create a settings embed showing channel, role, post time, timezone, and language, with all field names resolved via `t()`

#### Scenario: Similar results embed
- **WHEN** similar problems are displayed
- **THEN** the system SHALL create a similar results embed with all UI text resolved via `t()`

### Requirement: Consistent color and emoji mappings
The system SHALL use predefined color codes and emoji mappings for difficulty levels and problem attributes. These mappings SHALL NOT be localized (emojis are universal).

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
