## MODIFIED Requirements

### Requirement: Unified problem action buttons
The bot SHALL handle `view`, `desc`, `translate`, `inspire`, and `similar` actions for problems from all supported sources using the unified problem button format, including buttons rendered from problem overviews and similar-result responses.

#### Scenario: Unified problem action routing
- **WHEN** a user clicks a button with custom_id `problem|{source}|{problem_id}|{action}`
- **THEN** the bot SHALL parse `source`, `problem_id`, and `action` from the custom_id and route the interaction to the matching problem handler

#### Scenario: Overview detail button opens full problem card
- **WHEN** a user clicks an overview detail button with action `view`
- **THEN** the bot SHALL fetch the problem and send the full problem card with its interactive problem view instead of a description-only response

#### Scenario: Similar-result detail button opens full problem card
- **WHEN** a user clicks a similar-result detail button with action `view`
- **THEN** the bot SHALL fetch the problem and send the full problem card with its interactive problem view instead of a description-only response

## PBT Properties

### Property: View-button protocol round-trip
- **INVARIANT**: Every similar-result detail button that reaches the interaction handler can be parsed as `(source, problem_id, view)` without ambiguity
- **FALSIFICATION**: Generate valid and invalid `problem|...|...|view` custom_ids and assert that only valid ids route to the full-card handler

### Property: Stateless full-card routing
- **INVARIANT**: Clicking a similar-result detail button always reuses the existing `view` handler and does not require a separate similar-result interaction state store
- **FALSIFICATION**: Simulate clicks on similar-result detail buttons and assert the handler reaches the same full-card response path used by overview detail buttons
