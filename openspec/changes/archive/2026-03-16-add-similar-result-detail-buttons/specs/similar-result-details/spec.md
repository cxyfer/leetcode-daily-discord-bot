## ADDED Requirements

### Requirement: Similar-result responses expose direct problem detail entry
The system SHALL provide direct full-problem detail entry points for similar-result responses when the displayed result set can be rendered safely within the existing Discord button constraints.

#### Scenario: Slash `/similar` renders detail buttons for a safe result set
- **WHEN** a slash `/similar` response displays between 1 and 20 similar results and every displayed result has a valid `source` and `id`
- **THEN** the response SHALL include one detail button per displayed result using the existing `problem|{source}|{problem_id}|view` custom_id format

#### Scenario: Problem-card-triggered similar renders detail buttons for a safe result set
- **WHEN** a problem-card-triggered similar response displays between 1 and 25 similar results and every displayed result has a valid `source` and `id`
- **THEN** the response SHALL include one detail button per displayed result without changing the config-driven fetch behavior of the similar search

### Requirement: Similar-result detail entry fails closed when the response is not button-safe
The system SHALL degrade similar-result responses to embed-only whenever the displayed result set cannot safely and completely reuse the existing full-problem detail button protocol.

#### Scenario: Result count exceeds safe detail-button limit
- **WHEN** a similar-result response displays more than 25 results
- **THEN** the system SHALL send the result list as an embed without attaching any detail-button view

#### Scenario: Invalid routing fields prevent safe button creation
- **WHEN** any displayed similar result is missing a valid `source` or `id`
- **THEN** the system SHALL send the response as embed-only and SHALL NOT attach a partial subset of detail buttons

## PBT Properties

### Property: All-or-nothing detail affordance
- **INVARIANT**: A similar-result response either exposes one detail button for every displayed result or exposes no detail buttons at all
- **FALSIFICATION**: Generate result lists with mixed valid and invalid routing fields and assert that the builder never returns a partial button subset

### Property: Entry-point safety parity
- **INVARIANT**: The same safe result payload yields the same detail-button presence decision regardless of whether it comes from slash `/similar` or problem-card-triggered similar
- **FALSIFICATION**: Feed identical mocked result payloads through both entry points and compare whether a view is attached and how many buttons it contains
