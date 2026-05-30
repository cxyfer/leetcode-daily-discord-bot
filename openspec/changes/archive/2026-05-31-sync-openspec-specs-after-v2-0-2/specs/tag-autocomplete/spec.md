## MODIFIED Requirements

### Requirement: Tags autocomplete callback
The `/random` command SHALL provide dynamic autocomplete for the `tags` parameter using valid tags from the currently selected source, with defined fallback behavior for aggregate source selection.

#### Scenario: Autocomplete with selected source
- **WHEN** a user has selected source `leetcode` and starts typing in the `tags` field
- **THEN** the autocomplete SHALL fetch tags for `leetcode` and return up to 25 matching choices filtered by case-insensitive substring match

#### Scenario: Autocomplete with default source
- **WHEN** a user starts typing in the `tags` field without explicitly selecting a source
- **THEN** the autocomplete SHALL default to `leetcode` and return matching tags for that source

#### Scenario: Autocomplete with all source
- **WHEN** a user selects source `all` and starts typing in the `tags` field
- **THEN** the autocomplete SHALL use `leetcode` tag suggestions as the fallback tag source

#### Scenario: Autocomplete with no matching tags
- **WHEN** the user's input does not match any tags for the selected source
- **THEN** the autocomplete SHALL return an empty list of choices

#### Scenario: Autocomplete API failure graceful degradation
- **WHEN** the tags API fails during autocomplete
- **THEN** the autocomplete SHALL return an empty list of choices without displaying an error to the user

### Requirement: Startup tag preloading
The bot SHALL optionally preload tags for popular sources on startup to reduce cold-start latency for autocomplete.

#### Scenario: Preload on ready
- **WHEN** the bot fires the `on_ready` event
- **THEN** the bot SHALL initiate fire-and-forget cached tag requests for popular sources without blocking command sync or schedule initialization

#### Scenario: Preload failure does not block startup
- **WHEN** a preload API call fails
- **THEN** the failure SHALL be logged and SHALL NOT prevent the bot from starting or serving autocomplete requests
