## MODIFIED Requirements

### Requirement: Persistent button interaction system
The bot SHALL handle button interactions using persistent custom_id prefixes that survive bot restarts, with user-facing messages localized to the resolved locale.

#### Scenario: Button click after restart
- **WHEN** a user clicks a button on a message sent before a bot restart
- **THEN** the bot SHALL identify and handle the interaction based on the custom_id prefix

#### Scenario: Custom_id format differentiation
- **WHEN** a button interaction is received
- **THEN** the bot SHALL distinguish between unified problem buttons and config reset buttons without relying on localized labels

### Requirement: Problem description button
The bot SHALL display the full problem description when the description button is clicked, with surrounding UI text localized.

#### Scenario: Show problem description
- **WHEN** a user clicks the problem description button
- **THEN** the bot SHALL fetch the problem content and send it as an ephemeral message with localized UI text

#### Scenario: Content truncation
- **WHEN** the problem description exceeds Discord limits
- **THEN** the bot SHALL truncate within Discord limits and use localized truncation or error text when shown

### Requirement: LLM translation button
The bot SHALL provide problem translation via LLM when the translation button is clicked, with target language following the resolved locale.

#### Scenario: Translate to resolved locale
- **WHEN** a user clicks the translation button and LLM is configured
- **THEN** the bot SHALL translate the problem content to the resolved locale language

#### Scenario: Cached translation by locale
- **WHEN** translation for the same source, problem, and locale already exists in the cache
- **THEN** the bot SHALL return that cached translation without calling the LLM API

#### Scenario: LLM unavailable message
- **WHEN** LLM is not configured and translation is requested
- **THEN** the bot SHALL display a localized error message

### Requirement: LLM inspiration button
The bot SHALL provide problem-solving inspiration via LLM when the inspiration button is clicked, with output language following the resolved locale.

#### Scenario: Inspiration in resolved locale
- **WHEN** a user clicks the inspiration button and LLM is configured
- **THEN** the bot SHALL return structured hints in the resolved locale language

#### Scenario: Cached inspiration by locale
- **WHEN** inspiration for the same source, problem, and locale already exists in the cache
- **THEN** the bot SHALL return that cached inspiration without calling the LLM API

### Requirement: Localized interaction errors
All error and confirmation messages in interaction handling SHALL be resolved through the active locale.

#### Scenario: API error handling
- **WHEN** an API error occurs during interaction handling
- **THEN** the bot SHALL send a localized error message

#### Scenario: Permission error
- **WHEN** a user lacks required permissions for an interaction action
- **THEN** the bot SHALL send a localized permission error message

#### Scenario: Config reset confirmation
- **WHEN** a config reset is confirmed or cancelled
- **THEN** the bot SHALL respond with a localized confirmation message
