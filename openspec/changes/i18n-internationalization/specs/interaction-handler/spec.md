## MODIFIED Requirements

### Requirement: Persistent button interaction system
The bot SHALL handle button interactions using persistent custom_id prefixes that survive bot restarts, with all user-facing messages resolved via `t()`.

#### Scenario: Button click after restart
- **WHEN** a user clicks a button on a message sent before a bot restart
- **THEN** the bot SHALL correctly identify and handle the interaction based on the custom_id prefix

#### Scenario: Custom_id format differentiation
- **WHEN** a button interaction is received
- **THEN** the bot SHALL distinguish between unified problem buttons (`problem|{source}|{problem_id}|{action}`) and config reset buttons (`config_reset_confirm|...` / `config_reset_cancel|...`)

### Requirement: Problem description button
The bot SHALL display the full problem description when the description button is clicked, with all UI text localized.

#### Scenario: Show problem description
- **WHEN** a user clicks the problem description button
- **THEN** the bot SHALL fetch the problem content and send it as an ephemeral message with localized UI text

#### Scenario: Content truncation
- **WHEN** the problem description exceeds Discord limits
- **THEN** the bot SHALL truncate at 4000 characters for embeds or 1900 characters for direct messages, with localized truncation notice

### Requirement: LLM translation button
The bot SHALL provide problem translation via LLM when the translation button is clicked, with the target language following the guild locale.

#### Scenario: Translate to guild locale
- **WHEN** a user clicks the LLM translation button
- **THEN** the bot SHALL translate the problem content to the guild's resolved locale language

#### Scenario: Translation cache with locale
- **WHEN** a translation is requested
- **THEN** the bot SHALL check the LLM cache using (source, problem_id, locale) as the key

#### Scenario: LLM not enabled
- **WHEN** LLM is not configured and translation is requested
- **THEN** the bot SHALL display a localized error message

## ADDED Requirements

### Requirement: Localized error messages
All error and confirmation messages in interaction handling SHALL be resolved via `t()`.

#### Scenario: API error handling
- **WHEN** an API error occurs during interaction handling
- **THEN** the bot SHALL send a localized error message (e.g., `t("errors.api.network", locale)`)

#### Scenario: Permission error
- **WHEN** a user lacks required permissions
- **THEN** the bot SHALL send a localized permission error message

#### Scenario: Config reset confirmation
- **WHEN** a config reset is confirmed or cancelled
- **THEN** the bot SHALL respond with a localized confirmation message
