# tag-autocomplete Specification

## Purpose
Tags autocomplete capability for the `/random` command, providing dynamic tag suggestions fetched from upstream API with TTL-based caching.

## Requirements
### Requirement: Tags by source API method
The `OjApiClient` SHALL provide a `get_tags(source)` method that retrieves the valid tag list for a given problem source via `GET /api/v1/tags/{source}`.

#### Scenario: Successful tag retrieval
- **WHEN** `get_tags("leetcode")` is called
- **THEN** the method SHALL send a `GET /api/v1/tags/leetcode` request and return the response as a list of strings

#### Scenario: Empty tag list
- **WHEN** the API returns an empty array for a valid source
- **THEN** the method SHALL return an empty list

#### Scenario: Invalid source
- **WHEN** the API returns a 400 status for an invalid source
- **THEN** the method SHALL return an empty list without raising an exception

#### Scenario: API error
- **WHEN** the API returns a 500 status or network error
- **THEN** the method SHALL propagate standard error types (ApiNetworkError, ApiError)

### Requirement: TTL-cached tags access
The `OjApiClient` SHALL provide a `get_tags_cached(source)` method that caches tag results with a 24-hour TTL and supports stale fallback on API failure.

#### Scenario: Cache hit
- **WHEN** `get_tags_cached("leetcode")` is called and a cached result exists within the TTL (86400 seconds)
- **THEN** the method SHALL return the cached tags without making an API request

#### Scenario: Cache miss triggers API call
- **WHEN** `get_tags_cached("leetcode")` is called and no cached result exists
- **THEN** the method SHALL call `get_tags("leetcode")`, cache the result with a timestamp, and return the tags

#### Scenario: Expired cache with successful refresh
- **WHEN** `get_tags_cached("leetcode")` is called and the cache is older than TTL
- **THEN** the method SHALL attempt a fresh API call, update the cache on success, and return the fresh tags

#### Scenario: Expired cache with failed refresh returns stale
- **WHEN** `get_tags_cached("leetcode")` is called, the cache is older than TTL, and the API call fails
- **THEN** the method SHALL log a warning and return the stale cached tags

#### Scenario: No cache and API failure returns empty
- **WHEN** `get_tags_cached("spoj")` is called, no cache exists, and the API call fails
- **THEN** the method SHALL return an empty list without raising an exception

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
