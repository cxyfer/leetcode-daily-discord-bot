# leetcode-client Specification

## Purpose
TBD - created by archiving change init-project-specs. Update Purpose after archive.
## Requirements
### Requirement: Multi-domain LeetCode API client
The system SHALL support both leetcode.com and leetcode.cn domains with domain-specific GraphQL endpoints.

#### Scenario: Fetch from leetcode.com
- **WHEN** the client is configured for the US domain
- **THEN** API calls SHALL target leetcode.com endpoints

#### Scenario: Fetch from leetcode.cn
- **WHEN** the client is configured for the CN domain
- **THEN** API calls SHALL target leetcode.cn endpoints

### Requirement: Daily challenge fetching
The client SHALL fetch the current daily challenge with caching.

#### Scenario: Fetch today's challenge
- **WHEN** `get_daily_challenge()` is called
- **THEN** the client SHALL return the daily challenge, using cache if available and not expired

#### Scenario: Historical daily challenges
- **WHEN** a date parameter is provided
- **THEN** the client SHALL fetch the daily challenge for that specific date (available from April 2020 onwards)

#### Scenario: Monthly daily challenges
- **WHEN** monthly challenge data is requested
- **THEN** the client SHALL fetch all daily challenges for the specified month via background task processing

### Requirement: Problem data fetching
The client SHALL fetch detailed problem information including content, difficulty, tags, and ratings.

#### Scenario: Fetch problem by slug
- **WHEN** a problem title slug is provided
- **THEN** the client SHALL return full problem details via GraphQL

#### Scenario: Problem caching
- **WHEN** problem data exists in the database and is not expired (configurable TTL, default 1 hour)
- **THEN** the client SHALL return cached data without making an API call

### Requirement: User submission fetching
The client SHALL fetch recent accepted submissions for a given LeetCode user.

#### Scenario: Fetch submissions
- **WHEN** user submissions are requested
- **THEN** the client SHALL return recent accepted submissions with code and metadata

### Requirement: Retry logic with exponential backoff
The client SHALL retry failed API requests with exponential backoff.

#### Scenario: Transient API failure
- **WHEN** an API request fails with a transient error
- **THEN** the client SHALL retry with exponential backoff up to the configured max retries

### Requirement: Concurrency control
The client SHALL limit concurrent background API requests using a semaphore (default max 5).

#### Scenario: Concurrent request limiting
- **WHEN** more than 5 background API requests are in flight
- **THEN** additional requests SHALL wait until a slot becomes available

### Requirement: Background task tracking and graceful shutdown
The client SHALL track background tasks and support graceful shutdown.

#### Scenario: Graceful shutdown
- **WHEN** `shutdown()` is called
- **THEN** the client SHALL cancel all pending background tasks and wait for completion

