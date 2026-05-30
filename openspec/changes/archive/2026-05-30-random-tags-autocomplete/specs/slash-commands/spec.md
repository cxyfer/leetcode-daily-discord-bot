## ADDED Requirements

### Requirement: Random problem tags autocomplete
The `/random` command's `tags` parameter SHALL support dynamic autocomplete that fetches valid tags from the upstream API based on the currently selected source.

#### Scenario: Tags autocomplete appears when typing
- **WHEN** a user runs `/random`, selects a source, and begins typing in the `tags` field
- **THEN** the bot SHALL display up to 25 tag suggestions filtered by the typed input, fetched from the API for the currently selected source

#### Scenario: Tags autocomplete defaults to leetcode source
- **WHEN** a user begins typing in the `tags` field without having explicitly selected a source
- **THEN** the autocomplete SHALL use "leetcode" as the default source for tag suggestions

#### Scenario: Tags autocomplete updates when source changes
- **WHEN** a user changes the source value and then types in the `tags` field
- **THEN** the autocomplete SHALL fetch and display tags for the newly selected source

#### Scenario: Tags autocomplete empty result on API failure
- **WHEN** the tags API is unavailable during autocomplete
- **THEN** the bot SHALL return an empty autocomplete list without showing an error message, allowing the user to type tags manually

#### Scenario: Tags autocomplete handles no matches
- **WHEN** the user's typed input does not match any tag for the selected source
- **THEN** the bot SHALL return an empty autocomplete list (no choices displayed)
