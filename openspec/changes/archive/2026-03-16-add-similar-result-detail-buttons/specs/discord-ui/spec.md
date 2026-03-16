## ADDED Requirements

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

## PBT Properties

### Property: Button order preservation
- **INVARIANT**: Detail-button order always matches the displayed result order in the embed
- **FALSIFICATION**: Generate arbitrary valid result lists and assert that button labels and custom_ids preserve the same ordering as the rendered result list

### Property: Layout boundedness
- **INVARIANT**: No similar-result detail view contains more than 5 buttons in any row or more than 5 rows total
- **FALSIFICATION**: Generate valid result counts from 1 to 25 and assert each button row index stays within `0..4` with at most 5 buttons per row
