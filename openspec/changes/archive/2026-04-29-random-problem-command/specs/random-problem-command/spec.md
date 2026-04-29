# random-problem-command Specification

## ADDED Requirements

### Requirement: Random problem command
The `/random` command SHALL fetch and display a random LeetCode problem with optional filtering.

#### Scenario: Fetch random problem without filters
- **WHEN** a user runs `/random` without any filter parameters
- **THEN** the bot SHALL display a random problem from the entire LeetCode problem set with problem info, difficulty, tags, and interactive buttons

#### Scenario: Fetch random problem with difficulty filter
- **WHEN** a user runs `/random difficulty:Medium`
- **THEN** the bot SHALL display a random problem that has difficulty "Medium"

#### Scenario: Fetch random problem with tags filter
- **WHEN** a user runs `/random tags:Array`
- **THEN** the bot SHALL display a random problem that includes the "Array" tag

#### Scenario: Fetch random problem with rating range
- **WHEN** a user runs `/random rating_min:1500 rating_max:2000`
- **THEN** the bot SHALL display a random problem with rating between 1500 and 2000 (inclusive)

#### Scenario: Public toggle
- **WHEN** a user runs `/random` with the `public` parameter set to True
- **THEN** the response SHALL be visible to all users in the channel instead of ephemeral

#### Scenario: No matching problems
- **WHEN** a user runs `/random` with filter conditions that match no problems
- **THEN** the bot SHALL display an ephemeral error message showing the applied filter summary (e.g., "沒有找到符合 difficulty:Hard, tags:Array, rating:1500-2000 的題目")

### Requirement: Rating parameter validation
The `/random` command SHALL validate and normalize rating parameters.

#### Scenario: Rating min greater than max
- **WHEN** a user runs `/random rating_min:2000 rating_max:1500`
- **THEN** the bot SHALL automatically swap the values and use rating_min=1500, rating_max=2000

#### Scenario: Single rating bound
- **WHEN** a user runs `/random rating_min:1500` without rating_max
- **THEN** the bot SHALL use rating_min=1500 with no upper bound

#### Scenario: Rating boundary inclusive
- **WHEN** a user runs `/random rating_min:1500 rating_max:1500`
- **THEN** the bot SHALL display problems with rating exactly 1500

### Requirement: API client random problem method
The `OjApiClient` SHALL provide a `get_random_problem()` method that performs filtered random selection.

#### Scenario: Two-call random selection
- **WHEN** `get_random_problem()` is called with filters
- **THEN** the method SHALL first fetch the total count of matching problems, then fetch one random problem from the filtered set

#### Scenario: Zero results handling
- **WHEN** `get_random_problem()` is called and the API returns total count of 0
- **THEN** the method SHALL return a domain-level no-match result (not an API error)

#### Scenario: API error propagation
- **WHEN** `get_random_problem()` encounters API errors (429, timeout, network failure)
- **THEN** the method SHALL propagate standard error types (ApiRateLimitError, ApiNetworkError, ApiProcessingError)

### Requirement: UI component reuse
The `/random` command SHALL reuse existing UI components for consistent display.

#### Scenario: Problem embed format
- **WHEN** a random problem is successfully fetched
- **THEN** the bot SHALL use `create_problem_embed()` to generate the embed with difficulty color, tags, and rating

#### Scenario: Interactive buttons
- **WHEN** a random problem is displayed
- **THEN** the bot SHALL use `create_problem_view()` to generate buttons for description, translation, inspiration, and similar problems

#### Scenario: Button interaction routing
- **WHEN** a user clicks any button on a random problem
- **THEN** the interaction SHALL be routed through `InteractionHandlerCog` using the standard `problem|{source}|{id}|{action}` format
